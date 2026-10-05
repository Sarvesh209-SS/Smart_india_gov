from io import BytesIO
from pathlib import Path
from uuid import uuid4

from django.conf import settings


class StorageConfigurationError(Exception):
    pass


class DocumentStorageError(Exception):
    pass


def firebase_storage_enabled():
    bucket = settings.FIREBASE_STORAGE_BUCKET
    key_file = settings.FIREBASE_SERVICE_ACCOUNT_KEY
    if bool(bucket) != bool(key_file):
        raise StorageConfigurationError(
            "Set both FIREBASE_STORAGE_BUCKET and FIREBASE_SERVICE_ACCOUNT_KEY, or leave both empty."
        )
    return bool(bucket)


def _firebase_bucket():
    if not firebase_storage_enabled():
        raise StorageConfigurationError("Firebase Storage is not configured.")

    try:
        import firebase_admin
        from firebase_admin import credentials, storage
    except ImportError as error:
        raise StorageConfigurationError(
            "Firebase Storage is configured but firebase-admin is missing. Install requirements.txt."
        ) from error

    key_path = Path(settings.FIREBASE_SERVICE_ACCOUNT_KEY).expanduser()
    if not key_path.is_file():
        raise StorageConfigurationError(
            "FIREBASE_SERVICE_ACCOUNT_KEY must point to an existing service-account JSON file."
        )

    app_name = "smart-india-gov-storage"
    try:
        app = firebase_admin.get_app(app_name)
    except ValueError:
        try:
            app = firebase_admin.initialize_app(
                credentials.Certificate(str(key_path)),
                {"storageBucket": settings.FIREBASE_STORAGE_BUCKET},
                name=app_name,
            )
        except Exception as error:
            raise StorageConfigurationError("Firebase service-account configuration is invalid.") from error

    try:
        return storage.bucket(app=app)
    except Exception as error:
        raise DocumentStorageError("Could not connect to the Firebase Storage bucket.") from error


def save_document_file(document, uploaded_file):
    extension = Path(document.original_filename).suffix.lower()
    if firebase_storage_enabled():
        key = f"{document.owner_id}/{uuid4().hex}{extension}"
        blob = None
        try:
            blob = _firebase_bucket().blob(key)
            uploaded_file.seek(0)
            blob.upload_from_file(uploaded_file, rewind=True, content_type=document.file_type, timeout=60)
        except (StorageConfigurationError, DocumentStorageError):
            raise
        except Exception as error:
            if blob is not None:
                try:
                    blob.delete(timeout=60)
                except Exception:
                    pass
            raise DocumentStorageError("Firebase Storage upload failed. Check the network and bucket permissions.") from error
        document.storage_backend = document.StorageBackend.FIREBASE
        document.storage_key = key
        return

    try:
        document.file.save(document.original_filename, uploaded_file, save=False)
    except Exception as error:
        raise DocumentStorageError("Private document storage failed. Check the server's storage directory.") from error
    document.storage_backend = document.StorageBackend.LOCAL
    document.storage_key = document.file.name


def open_document_file(document):
    if document.storage_backend == document.StorageBackend.FIREBASE:
        try:
            content = _firebase_bucket().blob(document.storage_key).download_as_bytes(timeout=60)
            return BytesIO(content)
        except (StorageConfigurationError, DocumentStorageError):
            raise
        except Exception as error:
            raise DocumentStorageError("Could not download the private Firebase document.") from error
    return document.file.open("rb")


def delete_document_file(document):
    if document.storage_backend == document.StorageBackend.FIREBASE:
        if document.storage_key:
            try:
                _firebase_bucket().blob(document.storage_key).delete(timeout=60)
            except (StorageConfigurationError, DocumentStorageError):
                raise
            except Exception as error:
                raise DocumentStorageError("Could not delete the private Firebase document.") from error
    elif document.file:
        document.file.delete(save=False)
