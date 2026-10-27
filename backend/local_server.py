"""Isolated, zero-credential demo API for the OFFICIAL CourseSphere derivative.

Binds to loopback by default. Do not expose this demo on public interfaces.
"""
from __future__ import annotations
import json
import io
import sqlite3
import logging
import os
import re
import secrets
import sys
import time
import uuid
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import BoundedSemaphore, Lock
from urllib.parse import urlsplit
from .demo_store import DemoStore
from .security_core import DemoTokens, SecurityError, extract_bearer, safe_identifier, redact, strict_json_loads

MAX_BODY=32768
# Limit idle socket reads (request headers and body) in the local HTTP demo.
# This is not a global slow-client concurrency budget or a production WAF.
DEFAULT_CLIENT_READ_TIMEOUT=5.0
# Hard wall-clock budget for *all* network reads on one client connection.
# Repeated tiny writes must not be able to refresh this limit.
DEFAULT_REQUEST_READ_BUDGET=10.0
DEFAULT_MAX_ACTIVE_CLIENTS=64
BUCKETS=(.005,.01,.025,.05,.1,.25,.5,1,2.5,5)
LOGGER=logging.getLogger('coursesphere')
LOGGER.setLevel(logging.INFO)
handler=logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(message)s'))
LOGGER.addHandler(handler)

class Metrics:
    def __init__(self):
        self.lock=Lock()
        self.counts=defaultdict(int)
        self.bucket_counts=defaultdict(int)
        self.duration_sum=defaultdict(float)
    def observe(self,method,route,status,duration):
        label=(method,route,str(status//100)+'xx')
        with self.lock:
            self.counts[label]+=1
            self.duration_sum[(method,route)]+=duration
            for bucket in BUCKETS:
                if duration <= bucket:
                    self.bucket_counts[(method,route,bucket)]+=1
    def render(self,instance):
        lines=['# HELP coursesphere_http_requests_total HTTP requests grouped by status family',
               '# TYPE coursesphere_http_requests_total counter']
        with self.lock:
            for (m,r,s),v in sorted(self.counts.items()):
                lines.append(f'coursesphere_http_requests_total{{method="{m}",route="{r}",status_class="{s}",instance="{instance}"}} {v}')
            lines.extend(['# HELP coursesphere_http_duration_seconds Request latency', '# TYPE coursesphere_http_duration_seconds histogram'])
            for m,r in sorted(self.duration_sum):
                for b in BUCKETS:
                    n=self.bucket_counts[(m,r,b)]
                    lines.append(f'coursesphere_http_duration_seconds_bucket{{method="{m}",route="{r}",le="{b}",instance="{instance}"}} {n}')
                n=sum(v for (mm,rr,s),v in self.counts.items() if mm==m and rr==r)
                lines.append(f'coursesphere_http_duration_seconds_bucket{{method="{m}",route="{r}",le="+Inf",instance="{instance}"}} {n}')
                lines.append(f'coursesphere_http_duration_seconds_sum{{method="{m}",route="{r}",instance="{instance}"}} {self.duration_sum[(m,r)]}')
                lines.append(f'coursesphere_http_duration_seconds_count{{method="{m}",route="{r}",instance="{instance}"}} {n}')
        return '\n'.join(lines)+'\n'

class ServerContext:
    def __init__(self,path=None,secret=None,instance=None):
        self.store=DemoStore(path or os.getenv('DEMO_DB_PATH','/tmp/coursesphere-demo.sqlite3'))
        value=secret or os.getenv('DEMO_SIGNING_KEY','')
        if not value:
            # Safe for one local standalone process; dual replica compose MUST share a configured secret.
            value=secrets.token_urlsafe(40)
            LOGGER.warning(json.dumps({'level':'warning','message':'Ephemeral demo signing secret; tokens will not work across replicas'}))
        self.tokens=DemoTokens(value)
        self.instance=safe_identifier(instance or os.getenv('INSTANCE_ID','local'), 'instance')
        self.metrics=Metrics()

class BoundedHTTPServer(ThreadingHTTPServer):
    """Bound concurrent synthetic HTTP handlers before allocating threads.

    Excess connections are dropped immediately (they do not consume a handler
    thread). This is a local demo hardening measure, not production DDoS defense.
    """
    daemon_threads=True
    request_queue_size=64

    def __init__(self, server_address, RequestHandlerClass, max_active_clients=DEFAULT_MAX_ACTIVE_CLIENTS):
        self._handler_slots=BoundedSemaphore(max_active_clients)
        super().__init__(server_address, RequestHandlerClass)

    def process_request(self, request, client_address):
        if not self._handler_slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            # Exception before thread ownership is transferred to the handler.
            self._handler_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._handler_slots.release()


class DeadlineSocketReader(io.RawIOBase):
    """Bound the total monotonic time spent reading a synthetic HTTP request.

    BufferedReader calls readinto for network refills. Setting the timeout
    before *every* recv covers both header parsing and the request body,
    while preserving efficient buffered line parsing. The socket belongs to
    StreamRequestHandler; closing this wrapper must not close the connection.
    """

    def __init__(self, sock, idle_timeout: float, deadline: float):
        super().__init__()
        self.sock = sock
        self.idle_timeout = idle_timeout
        self.deadline = deadline

    def readable(self):
        return True

    def readinto(self, target):
        if self.closed:
            raise ValueError('Read on closed stream')
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Synthetic request read budget exhausted')
        self.sock.settimeout(min(self.idle_timeout, remaining))
        return self.sock.recv_into(target)


class CourseSphereHandler(BaseHTTPRequestHandler):
    server_version='CourseSphereLab/1.0'
    sys_version=''
    context:ServerContext
    read_timeout=DEFAULT_CLIENT_READ_TIMEOUT
    request_read_budget=DEFAULT_REQUEST_READ_BUDGET

    def setup(self):
        # Both idle and total read budgets begin before the HTTP request line.
        # A client that sends one byte every (idle_timeout / 2) still expires.
        deadline = time.monotonic() + self.request_read_budget
        self.request.settimeout(self.read_timeout)
        super().setup()
        old_reader = self.rfile
        self.rfile = io.BufferedReader(
            DeadlineSocketReader(self.request, self.read_timeout, deadline),
            buffer_size=8192,
        )
        old_reader.close()

    def log_message(self,format,*args):
        pass

    def do_GET(self): self.dispatch('GET')
    def do_POST(self): self.dispatch('POST')
    def do_PUT(self): self.dispatch('PUT')
    def do_DELETE(self): self.dispatch('DELETE')
    def do_OPTIONS(self):
        self.send_response(405)
        self.send_header('Allow','GET, POST, PUT, DELETE')
        self.send_header('Content-Length','0')
        self.end_headers()

    def dispatch(self,method):
        start=time.monotonic()
        parsed=urlsplit(self.path)
        path=parsed.path
        normalized='/api/courses/:course_id/lessons/:lesson_id' if re.fullmatch(r'/api/courses/\d+/lessons/\d+',path) else (
            '/api/courses/:course_id/lessons' if re.fullmatch(r'/api/courses/\d+/lessons',path) else (
            '/api/courses/:course_id' if re.fullmatch(r'/api/courses/\d+',path) else path if path in {'/api/health','/api/ready','/metrics','/api/demo/session','/api/courses','/api/events'} else '/not-found'))
        status=200
        request_id=str(uuid.uuid4())
        try:
            # Reject ambiguous framing before authentication, route dispatch or
            # reading a request body. This server never decodes chunked bodies.
            lengths = self.headers.get_all('Content-Length', [])
            # Proxies and application servers may choose different values for
            # duplicate security-sensitive fields. Refuse to resolve ambiguity.
            repeated = any(len(self.headers.get_all(name, [])) > 1 for name in
                           ('Authorization', 'Content-Type', 'Host', 'Content-Length'))
            if (parsed.scheme or parsed.netloc or self.path.startswith('//')
                    or self.headers.get('Transfer-Encoding') is not None
                    or repeated
                    or (lengths and re.fullmatch(r'[0-9]{1,10}', lengths[0]) is None)
                    or (self.request_version == 'HTTP/1.1'
                        and len(self.headers.get_all('Host', [])) != 1)):
                raise SecurityError('Invalid HTTP request framing', 400)
            result,status,mime=self.route(method,path)
        except SecurityError as e:
            if e.status in (400, 408, 413):
                self.close_connection=True
            status=e.status
            result={'error':str(e),'request_id':request_id}
            mime='application/json'
        except (TimeoutError, ConnectionError, OSError):
            # A partially delivered body must not be treated as a server 500;
            # terminate this request connection instead of accepting pipelining.
            self.close_connection=True
            status=408
            result={'error':'Request body timed out or disconnected','request_id':request_id}
            mime='application/json'
        except Exception:
            # Never log exception tracebacks: database/SDK exceptions may
            # interpolate PII, bearer tokens or other request data.
            LOGGER.error(json.dumps({'event':'http_internal_error','request_id':request_id}))
            status=500
            result={'error':'Internal server error','request_id':request_id}
            mime='application/json'
        if isinstance(result,(dict,list)):
            body=json.dumps(result,ensure_ascii=False).encode('utf-8')
        else:
            body=str(result).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',mime+'; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'")
        self.send_header('X-Request-ID',request_id)
        self.send_header('X-CourseSphere-Instance',self.context.instance)
        try:
            self.end_headers()
            if method != 'HEAD': self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError):
            # The peer left before reading the response; avoid a traceback and
            # release the handler thread without emitting request data.
            self.close_connection=True
        self.context.metrics.observe(method,normalized,status,time.monotonic()-start)
        LOGGER.info(json.dumps({'event':'http_request','time':int(time.time()),'request_id':request_id,
                                'method':method,'route':normalized,'status':status,'instance':self.context.instance,
                                'duration_ms':round((time.monotonic()-start)*1000,2)}))

    def json_input(self):
        content_type=self.headers.get('Content-Type','').split(';')[0].strip().lower()
        if content_type!='application/json':
            raise SecurityError('Content-Type must be application/json',415)
        try:
            length=int(self.headers.get('Content-Length','0'))
        except (ValueError,TypeError):
            raise SecurityError('Invalid Content-Length',400) from None
        if length<=0 or length>MAX_BODY:
            raise SecurityError('Request body too large or missing',413)
        try:
            raw=self.rfile.read(length)
            if len(raw)!=length:
                # A short body is invalid even if its prefix is valid JSON.
                raise SecurityError('Incomplete request body',400)
            return strict_json_loads(raw)
        except (ValueError,UnicodeDecodeError):
            raise SecurityError('Malformed JSON',400) from None

    def principal(self):
        return self.context.tokens.verify(extract_bearer(self.headers.get('Authorization')))

    def route(self,method,path):
        if method=='GET' and path in {'/api/health','/api/ready'}:
            if path=='/api/ready':
                try:
                    with self.context.store.connect() as db:
                        if db.execute('SELECT 1').fetchone() is None:
                            raise sqlite3.DatabaseError('No readiness result')
                except sqlite3.Error:
                    raise SecurityError('Dependency unavailable', 503) from None
            return {'status':'ok','instance':self.context.instance,'mode':'synthetic-demo'},200,'application/json'
        if method=='GET' and path=='/metrics':
            return self.context.metrics.render(self.context.instance),200,'text/plain; version=0.0.4'
        if method=='POST' and path=='/api/demo/session':
            # Intentionally public local-only demo role selector, never deploy this route to the internet.
            uid=self.json_input()
            if not isinstance(uid,dict) or uid.get('uid') not in {'alice','bob','student','admin'}:
                raise SecurityError('Unknown synthetic demo user')
            principal={'alice':'instructor','bob':'instructor','student':'student','admin':'admin'}
            name=uid['uid']
            # Shared SQLite rate limiting across replicas keyed by remote client address.
            # Trusted proxy is not consulted, preventing forged X-Forwarded-For bypass.
            if not self.context.store.hit_rate_limit('session:'+self.client_address[0],int(time.time()),30,60):
                raise SecurityError('Too many login requests',429)
            return {'access_token':self.context.tokens.issue(name,principal[name]),'role':principal[name],'uid':name,'expires_in':1800},200,'application/json'
        if not path.startswith('/api/'):
            raise SecurityError('Route not found',404)
        user=self.principal()
        if method=='GET' and path=='/api/events':
            return {'events':self.context.store.list_events(user)},200,'application/json'
        if path=='/api/courses':
            if method=='GET': return {'courses':self.context.store.list_courses()},200,'application/json'
            if method=='POST':
                created=self.context.store.create_course(user,self.json_input())
                return created,201,'application/json'
        match=re.fullmatch(r'/api/courses/(\d+)(?:/lessons(?:/(\d+))?)?',path)
        if not match: raise SecurityError('Route not found',404)
        course_id=int(match.group(1))
        if course_id>2147483647: raise SecurityError('Invalid course ID')
        lesson_id=int(match.group(2)) if match.group(2) else None
        if lesson_id is not None and lesson_id>2147483647: raise SecurityError('Invalid lesson ID')
        if '/lessons' not in path:
            if method=='PUT':
                try:
                    result=self.context.store.update_course(course_id,user,self.json_input())
                except SecurityError as e:
                    self.context.store.log_event('course.update',user,course_id,'denied')
                    raise
                return result,200,'application/json'
            if method=='DELETE':
                result=self.context.store.delete_course(course_id,user)
                return result,200,'application/json'
        elif lesson_id is None:
            if method=='GET': return {'lessons':self.context.store.list_lessons(course_id)},200,'application/json'
            if method=='POST':
                result=self.context.store.create_lesson(course_id,user,self.json_input())
                return result,201,'application/json'
        else:
            if method=='PUT':
                result=self.context.store.update_lesson(course_id,lesson_id,user,self.json_input())
                return result,200,'application/json'
            if method=='DELETE':
                result=self.context.store.delete_lesson(course_id,lesson_id,user)
                return result,200,'application/json'
        raise SecurityError('Method not allowed',405)


def make_server(host='127.0.0.1',port=8091,db_path=None,secret=None,instance=None,read_timeout=DEFAULT_CLIENT_READ_TIMEOUT,max_active_clients=DEFAULT_MAX_ACTIVE_CLIENTS,request_read_budget=DEFAULT_REQUEST_READ_BUDGET):
    if (isinstance(read_timeout,bool) or not isinstance(read_timeout,(int,float))
            or not 0.1 <= read_timeout <= 30.0):
        raise ValueError('Invalid demo client read timeout')
    if (isinstance(request_read_budget,bool) or not isinstance(request_read_budget,(int,float))
            or not 0.1 <= request_read_budget <= 120.0):
        raise ValueError('Invalid absolute request read budget')
    if type(max_active_clients) is not int or not 1 <= max_active_clients <= 512:
        raise ValueError('Invalid maximum active demo clients')
    ctx=ServerContext(path=db_path,secret=secret,instance=instance)
    timeout_value=float(read_timeout)
    budget_value=float(request_read_budget)
    class BoundHandler(CourseSphereHandler):
        context=ctx
        read_timeout=timeout_value
        request_read_budget=budget_value
    return BoundedHTTPServer((host,port),BoundHandler,max_active_clients=max_active_clients)


def main():
    if os.getenv('APP_MODE')!='demo':
        raise SystemExit('Refusing startup: set APP_MODE=demo for isolated synthetic mode.')
    host=os.getenv('BIND_HOST','127.0.0.1')
    port=int(os.getenv('PORT','8091'))
    if host not in {'127.0.0.1','localhost','::1'} and os.getenv('ALLOW_CONTAINER_BIND')!='yes':
        raise SystemExit('Refusing non-loopback interface without ALLOW_CONTAINER_BIND=yes')
    # No user-provided environment override: local-only default is bounded.
    httpd=make_server(host,port)
    LOGGER.info(json.dumps({'event':'server_started','mode':'demo','bind_host':host,'port':port,'instance':httpd.RequestHandlerClass.context.instance}))
    httpd.serve_forever()

if __name__=='__main__': main()
