# Firebase adapter remains for the OFFICIAL app; sandbox never uses this module.
import os
if __package__:
    from .shared_quota import debit, QuotaExceeded
else:
    from shared_quota import debit, QuotaExceeded
from functools import lru_cache
if __package__:
    from .firebase_configuration import validate_emulators, validate_live, validate_existing_default_app
else:
    from firebase_configuration import validate_emulators, validate_live, validate_existing_default_app

@lru_cache(maxsize=1)
def _firebase():
    """Connect only to an explicitly authorized project or isolated local emulators.

    Emulators use a demo-* project ID and loopback-only hostnames. This prevents
    accidentally contacting the original CourseSphere Firebase project in tests.
    """
    import firebase_admin
    from firebase_admin import credentials, auth, db

    selected_mode = os.getenv("COURSESPHERE_USE_FIREBASE_EMULATORS", "0")
    if selected_mode not in {"0", "1"}:
        raise RuntimeError("Invalid Firebase mode; expected 0 or 1")
    emulator_mode = selected_mode == "1"
    if emulator_mode:
        from google.auth.credentials import Credentials

        project_id = os.getenv("GCLOUD_PROJECT", "")
        auth_host = os.getenv("FIREBASE_AUTH_EMULATOR_HOST", "")
        db_host = os.getenv("FIREBASE_DATABASE_EMULATOR_HOST", "")
        validate_emulators(project_id, auth_host, db_host,
                           os.getenv("FIREBASE_CREDENTIALS_FILE", ""))

        class EmulatorOwnerCredentials(Credentials):
            """Never used off-loopback; 'owner' is the local RTDB emulator admin token."""
            def __init__(self):
                super().__init__()
                self.token = "owner"

            def refresh(self, request):
                self.token = "owner"

        class LocalEmulatorCredential(credentials.Base):
            def get_credential(self):
                return EmulatorOwnerCredentials()

        database_url = f"https://{project_id}-default-rtdb.firebaseio.com"
        try:
            existing_app = firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(
                LocalEmulatorCredential(),
                {"projectId": project_id, "databaseURL": database_url},
            )
        else:
            validate_existing_default_app(
                existing_app, project_id, database_url, emulator=True,
                emulator_credential_type=LocalEmulatorCredential)
        return auth, db

    cred_path = os.getenv("FIREBASE_CREDENTIALS_FILE", "")
    db_url = os.getenv("FIREBASE_DATABASE_URL", "")
    validate_live(cred_path, db_url,
                  os.getenv("FIREBASE_AUTH_EMULATOR_HOST", ""),
                  os.getenv("FIREBASE_DATABASE_EMULATOR_HOST", ""))
    try:
        existing_app = firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(credentials.Certificate(cred_path), {"databaseURL": db_url})
    else:
        validate_existing_default_app(existing_app, '', db_url, emulator=False)
    return auth, db

class _LazyAuth:
    def __getattr__(self, name): return getattr(_firebase()[0],name)
class _LazyDB:
    def __getattr__(self, name): return getattr(_firebase()[1],name)
auth=_LazyAuth()
db=_LazyDB()

class Firebase:
    @staticmethod
    def probe_dependencies() -> bool:
        """Readiness only: verify both local/authorized Auth and RTDB respond.

        The private, tiny marker does not need to exist. Do NOT query the RTDB
        root: that could transfer other users' data into a healthcheck. Errors
        are deliberately handled by the readiness caller, not exposed to HTTP.
        """
        auth_client, db_client = _firebase()
        auth_client.list_users(max_results=1)
        db_client.reference('server_security/readiness').get()
        return True

    @staticmethod
    def enforce_quota(uid: str, action: str):
        """Use a privileged RTDB transaction, shared across Flask replicas.

        Client writes are denied by ``ops/firebase/database.rules.json``.
        Validated Flask handlers write via Admin; quota counters stay private.
        """
        allowed = debit(db.reference, uid, action)
        if not allowed:
            raise QuotaExceeded("Quota exceeded")

    @staticmethod
    def create_user(email: str, password: str):
        try:
            user = auth.create_user(email=email, password=password)
            user_data = {
            "message": "User created successfully",
            "user_id": user.uid,
            "email": user.email,
            } 
            return user_data
        except Exception as e:
            raise Exception(f"Error creating user: {str(e)}")
        
    @staticmethod
    def delete_user(uid: str):
        try:
            auth.delete_user(uid)
            ref = db.reference(f"users/{uid}")
            ref.delete()
        except Exception as e:
            raise Exception(f"Error deleting user: {str(e)}")

    @staticmethod
    def verify_id_token(id_token: str):
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            raise Exception(f"Error verifying ID token: {str(e)}")

    @staticmethod
    def set_user_info(uid: str, user_info: dict):
        try:
            ref = db.reference(f"users/{uid}/info")
            ref.set(user_info)
        except Exception as e:
            raise Exception(f"Error setting user info: {str(e)}")

    @staticmethod
    def get_user_info(uid: str):
        try:
            ref = db.reference(f"users/{uid}/info")
            user_info = ref.get()
            return user_info
        except Exception as e:
            raise Exception(f"Error getting user info: {str(e)}")
        
    @staticmethod
    def try_get_user_info(id_token):
        try:
            return Firebase.get_user_info(Firebase.verify_id_token(id_token).get('uid'))
        except Exception:
            return None



    @staticmethod
    def update_user_info(uid: str, updates: dict):
        try:
            ref = db.reference(f"users/{uid}/info")
            ref.update(updates)
        except Exception as e:
            raise Exception(f"Error updating user info: {str(e)}")
    
    @staticmethod
    def create_document(collection: str, document_id: str, data: dict):
        """
        Creates a document in a specified collection.
        
        :param collection: The name of the collection.
        :param document_id: The ID of the document to create.
        :param data: A dictionary of the data to store in the document.
        """
        try:
            ref = db.reference(f"{collection}/{document_id}")
            ref.set(data)
        except Exception as e:
            raise Exception(f"Error creating document: {str(e)}")

    @staticmethod
    def get_document(collection: str, document_id: str):
        """
        Retrieves a document from a specified collection.
        
        :param collection: The name of the collection.
        :param document_id: The ID of the document to retrieve.
        :return: The document data as a dictionary.
        """
        try:
            ref = db.reference(f"{collection}/{document_id}")
            document = ref.get()
            return document
        except Exception as e:
            raise Exception(f"Error retrieving document: {str(e)}")

    @staticmethod
    def update_document(collection: str, document_id: str, updates: dict):
        """
        Updates a document in a specified collection.
        
        :param collection: The name of the collection.
        :param document_id: The ID of the document to update.
        :param updates: A dictionary of the updates to apply to the document.
        """
        try:
            ref = db.reference(f"{collection}/{document_id}")
            ref.update(updates)
        except Exception as e:
            raise Exception(f"Error updating document: {str(e)}")

    @staticmethod
    def delete_document(collection: str, document_id: str):
        """
        Deletes a document from a specified collection.
        
        :param collection: The name of the collection.
        :param document_id: The ID of the document to delete.
        """
        try:
            ref = db.reference(f"{collection}/{document_id}")
            ref.delete()
        except Exception as e:
            raise Exception(f"Error deleting document: {str(e)}")
        

    @staticmethod
    def list_chats(uid: str):
        """List at most 50 of this verified user's chats; no cross-user lookup."""
        ref = db.reference(f"users/{uid}/chats")
        value = ref.order_by_key().limit_to_last(50).get() or {}
        result = []
        for chat_id, body in value.items():
            if not isinstance(body, dict):
                continue
            messages = body.get("messages") or {}
            timestamp = ""
            if isinstance(messages, dict) and messages:
                last = list(messages.values())[-1]
                if isinstance(last, dict) and isinstance(last.get("timestamp"), str):
                    timestamp = last["timestamp"][:64]
            result.append({"title": chat_id[:64], "timestamp": timestamp})
        return result

    @staticmethod
    def save_chat(uid: str, chat_id: str, messages: list):
        """Atomically upsert messages by their opaque IDs.

        Deterministic child keys make client retries idempotent, rather than
        creating a duplicate message for every retried HTTP request.
        Input validation happens in the Flask handler before this call.
        """
        updates = {message["messageID"]: message for message in messages}
        if not updates:
            return
        try:
            ref = db.reference(f"users/{uid}/chats/{chat_id}/messages")
            ref.update(updates)
        except Exception as exc:
            raise RuntimeError("Unable to save chat") from exc

    @staticmethod
    def delete_chat(uid: str, chat_id: str):
        try:
            ref = db.reference(f"users/{uid}/chats/{chat_id}")
            ref.delete()  # Deletes the entire chat session
        except Exception as e:
            raise Exception(f"Error deleting chat session: {str(e)}")
