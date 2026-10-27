from flask import Flask, request, jsonify, g, Response
import os
import json
import logging
import time
import uuid
from flask_cors import CORS
from cors_policy import parse_allowed_origins
from werkzeug.exceptions import HTTPException
from werkzeug.serving import WSGIRequestHandler
from query_manager import QueryManager
from firebase import Firebase
from main import hashFunction
from security_core import SecurityError, validate_profile, validate_messages, extract_bearer, safe_identifier, bounded_text
from observability import HTTPMetrics
from metrics_access import metrics_authorized
from request_correlation import correlation_id, replica_label
from readiness import DependencyReadiness
from shared_quota import QuotaExceeded, QuotaUnavailable
from strict_request_json import parse_object as parse_strict_request_object

app = Flask(__name__)
# Gunicorn disables its raw access log; emit the application's safe events.
# Explicit configuration is needed: Flask's default WARNING level drops INFO.
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(message)s'))
app.logger.handlers = [log_handler]
app.logger.setLevel(logging.INFO)
app.logger.propagate = False


class SafeRequestHandler(WSGIRequestHandler):
    """The route-template JSON event replaces Werkzeug's raw URL access line."""
    def log_request(self, code='-', size='-'):
        pass

    def log_error(self, format, *args):
        app.logger.warning('{"event":"http_transport_error"}')


app.config['SAFE_REQUEST_HANDLER'] = SafeRequestHandler
metrics = HTTPMetrics()
dependency_readiness = DependencyReadiness(ttl_seconds=5.0)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
allowed_origins = parse_allowed_origins(os.getenv("ALLOWED_ORIGINS"))
CORS(app, origins=allowed_origins, allow_headers=["Content-Type", "Authorization"])

# Original course blueprint is not registered: optional legacy routes need a real
# SQLite schema and security review before activation.

@app.before_request
def start_request():
    g.request_started = time.monotonic()
    g.request_id = correlation_id(
        request.headers.get('X-Request-ID'),
        trust_gateway=os.getenv('COURSESPHERE_TRUST_GATEWAY_REQUEST_ID') == '1')
    # Reject tokens carried in URLs, even when a valid Bearer header is present.
    # Query strings often reach browser history, reverse proxies and analytics.
    if any(key.lower() in {"id_token", "access_token", "auth_token", "api_key"}
           for key in request.args):
        return error_response("Use Authorization header", 401)

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Request-ID"] = getattr(g, "request_id", "unknown")
    # Stable low-cardinality label. The integration proof must distinguish two
    # *actual* Flask replicas; reaching the same process twice is insufficient.
    response.headers["X-CourseSphere-Replica"] = replica_label(
        os.getenv('COURSESPHERE_REPLICA_NAME'))
    # Never log token values or original URLs (query strings could contain tokens).
    if request.path != "/metrics":
        metrics.observe(request.method, request.url_rule.rule if request.url_rule else "unmatched", response.status_code,
                        time.monotonic() - getattr(g, "request_started", time.monotonic()))
    app.logger.info(json.dumps({
        "event": "http_request",
        "method": request.method,
        "route": request.url_rule.rule if request.url_rule is not None else "unmatched",
        "status": response.status_code,
        "duration_ms": round((time.monotonic() - getattr(g, "request_started", time.monotonic())) * 1000, 2),
        "request_id": getattr(g, "request_id", "unknown"),
        "replica": replica_label(os.getenv('COURSESPHERE_REPLICA_NAME')),
    }, separators=(",", ":")))
    return response

@app.errorhandler(413)
def content_too_large(_exc):
    return error_response("Request body too large", 413)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "coursesphere-api"}), 200


@app.get("/ready")
def ready():
    """Dependency readiness, separate from the process-liveness /health.

    Intentionally never reports Firebase project IDs, errors or credentials.
    A transient outage returns 503 so local operators can see degradation.
    """
    if dependency_readiness.ready(Firebase.probe_dependencies):
        return jsonify({"status": "ready", "service": "coursesphere-api"}), 200
    return jsonify({"status": "unavailable", "service": "coursesphere-api"}), 503


@app.get("/metrics")
def prometheus_metrics():
    """Private metrics: opt-in; loopback or a Docker-secret bearer token."""
    if not metrics_authorized(request.remote_addr, request.headers.get("Authorization")):
        return error_response("Not found", 404)
    # Prometheus scrapes BOTH Flask replicas directly. A scrape is itself the
    # periodic dependency check; no extra account, exporter or cron is needed.
    # Gate authorization FIRST: unauthorized callers must never trigger Firebase.
    # The shared 5s readiness cache coalesces simultaneous /ready and /metrics.
    metrics.set_firebase_readiness(dependency_readiness.ready(Firebase.probe_dependencies))
    return Response(metrics.render(), content_type="text/plain; version=0.0.4; charset=utf-8")


def audit_auth(result: str) -> None:
    """Audit the outcome only: never log Firebase UID, token, IP or query."""
    route = request.url_rule.rule if request.url_rule is not None else "unmatched"
    metrics.observe_auth(result, route)
    app.logger.info(json.dumps({
        "event": "authentication", "result": result,
        "route": route, "request_id": getattr(g, "request_id", "unknown"),
    }, separators=(",", ":")))


def verified_uid():
    try:
        token = extract_bearer(request.headers.get("Authorization"))
        decoded = Firebase.verify_id_token(token)
        uid = decoded.get("uid")
        if not isinstance(uid, str) or not uid:
            raise SecurityError("Invalid or expired token", 401)
    except Exception:
        # Preserve safe error messages; normalize all service failures as 401.
        audit_auth("denied")
        raise SecurityError("Invalid or expired token", 401) from None
    audit_auth("accepted")
    return uid

def request_json_object():
    """Use the same strict JSON validation on every official POST endpoint."""
    # Flask enforces MAX_CONTENT_LENGTH while obtaining request bytes.
    return parse_strict_request_object(request.get_data(cache=False), request.mimetype)


success_response = lambda data, code: (jsonify(data), code)
error_response = lambda error, code: (jsonify({'error': error}), code)

@app.route("/users/create", methods=["POST"])
def create_user():
    # The original route invoked Firebase Admin (a privileged API) for anonymous
    # callers. Sign-up now uses createUserWithEmailAndPassword on the frontend.
    # Keep 410 to prevent an old client accidentally using the privileged path.
    return error_response("Use Firebase Authentication client signup", 410)

@app.route("/users/info", methods=["POST"])
def set_user_info(): 
    try:
        uid = verified_uid()
        data = request_json_object()
    except SecurityError as e:
        return error_response(str(e), e.status)
    try:
        user_info = validate_profile(data)
        # The limit is enforced by a shared Firebase transaction across replicas.
        Firebase.enforce_quota(uid, "profile_write")
        Firebase.set_user_info(uid, user_info) 
        return success_response({"message": "User info set successfully", "uid": uid}, 200)
    except SecurityError as e:
        return error_response(str(e), e.status)
    except QuotaExceeded:
        return error_response("Too many requests", 429)
    except QuotaUnavailable:
        return error_response("Quota service unavailable", 503)
    except HTTPException:
        # Preserve Flask protocol errors (notably MAX_CONTENT_LENGTH -> 413).
        raise
    except Exception:
        return error_response("Unable to update user info", 500)
        
@app.route("/users/info", methods=["GET"])
def get_user_info():
    try:
        uid = verified_uid()
        user_info = Firebase.get_user_info(uid)
        return success_response(user_info, 200)
    except SecurityError as e:
        return error_response(str(e), e.status)
    except HTTPException:
        # Preserve Flask protocol errors (notably MAX_CONTENT_LENGTH -> 413).
        raise
    except Exception:
        return error_response("Unable to retrieve user info", 500)

@app.route("/users/query", methods=["POST"])
def get_user_query():
    try:
        uid = verified_uid()
        payload = request_json_object()
        if not isinstance(payload, dict):
            raise SecurityError("JSON object required")
        query = bounded_text(payload.get("query"), "query", 2000, 1)
        Firebase.enforce_quota(uid, "recommendation")
        user_info = Firebase.get_user_info(uid) or {}
        return success_response(QueryManager(query, user_info).response, 200)
    except SecurityError as e:
        return error_response(str(e), e.status)
    except QuotaExceeded:
        return error_response("Too many requests", 429)
    except QuotaUnavailable:
        return error_response("Quota service unavailable", 503)
    except HTTPException:
        # Preserve Flask protocol errors (notably MAX_CONTENT_LENGTH -> 413).
        raise
    except Exception:
        return error_response("Unable to process query", 500)

@app.route('/hash', methods=['POST'])
def generate_message_id():
    try:
        uid = verified_uid()
        data = request_json_object()
        if not isinstance(data, dict):
            raise SecurityError("JSON object required")
        Firebase.enforce_quota(uid, "message_id")
        message_id = hashFunction(data)
        return jsonify({"messageID": message_id}), 200
    except SecurityError as e:
        return error_response(str(e), e.status)
    except QuotaExceeded:
        return error_response("Too many requests", 429)
    except QuotaUnavailable:
        return error_response("Quota service unavailable", 503)
    except HTTPException:
        # Preserve Flask protocol errors (notably MAX_CONTENT_LENGTH -> 413).
        raise
    except Exception:
        return error_response("Unable to generate message ID", 500)

@app.route("/chats", methods=["GET"])
def list_chats():
    try:
        user_id = verified_uid()
        chats = Firebase.list_chats(user_id)
        return success_response({"chats": chats}, 200)
    except SecurityError as e:
        return error_response(str(e), e.status)
    except HTTPException:
        # Preserve Flask protocol errors (notably MAX_CONTENT_LENGTH -> 413).
        raise
    except Exception:
        return error_response("Unable to retrieve chats", 500)

@app.route("/chats/<chat_id>/messages", methods=["POST"])
def save_chat(chat_id):
    try:
        user_id = verified_uid()
        safe_identifier(chat_id, "chat_id")
        messages = validate_messages(request_json_object())
        # Count authenticated writes across every Flask replica before modifying
        # shared state. A broken quota store must never silently bypass controls.
        Firebase.enforce_quota(user_id, "chat_write")
        Firebase.save_chat(user_id, chat_id, messages)
        return jsonify({"message": "Messages saved successfully"}), 200
    except SecurityError as e:
        return error_response(str(e), e.status)
    except QuotaExceeded:
        return error_response("Too many requests", 429)
    except QuotaUnavailable:
        return error_response("Quota service unavailable", 503)
    except HTTPException:
        # Preserve Flask protocol errors (notably MAX_CONTENT_LENGTH -> 413).
        raise
    except Exception:
        return error_response("Unable to save messages", 500)

@app.route("/chats/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    try:
        user_id = verified_uid()
        safe_identifier(chat_id, "chat_id")
        Firebase.enforce_quota(user_id, "chat_delete")
        Firebase.delete_chat(user_id, chat_id)
        return success_response({"message": "Chat deleted successfully"}, 200)
    except SecurityError as e:
        return error_response(str(e), e.status)
    except QuotaExceeded:
        return error_response("Too many requests", 429)
    except QuotaUnavailable:
        return error_response("Quota service unavailable", 503)
    except HTTPException:
        # Preserve Flask protocol errors (notably MAX_CONTENT_LENGTH -> 413).
        raise
    except Exception:
        return error_response("Unable to delete chat", 500)


if __name__ == '__main__':
    app.run(debug=False, request_handler=SafeRequestHandler)
