from pathlib import Path
from zipfile import BadZipFile, ZipFile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".jpg", ".jpeg", ".png"}
FILE_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def validate_upload(f):
    if f.size > settings.MAX_UPLOAD_BYTES:
        raise ValidationError(_("File is too large. The maximum size is 5 MB."))
    if f.size == 0:
        raise ValidationError(_("The selected file is empty."))

    extension = Path(f.name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(_("Unsupported file type. Upload PDF, DOC, DOCX, TXT, JPG, JPEG, or PNG."))

    head = f.read(4096)
    f.seek(0)
    is_valid = False
    if extension == ".pdf":
        is_valid = head.startswith(b"%PDF-")
    elif extension == ".doc":
        is_valid = head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    elif extension == ".docx":
        try:
            with ZipFile(f) as archive:
                is_valid = "[Content_Types].xml" in archive.namelist() and "word/document.xml" in archive.namelist()
        except (BadZipFile, OSError):
            is_valid = False
        finally:
            f.seek(0)
    elif extension in {".jpg", ".jpeg"}:
        is_valid = head.startswith(b"\xff\xd8\xff")
    elif extension == ".png":
        is_valid = head.startswith(b"\x89PNG\r\n\x1a\n")
    elif extension == ".txt":
        try:
            f.seek(0)
            content = f.read()
            is_valid = b"\x00" not in content and bool(content.decode("utf-8-sig").strip())
        except UnicodeDecodeError:
            is_valid = False
        finally:
            f.seek(0)

    if not is_valid:
        raise ValidationError(_("The file contents do not match the selected file type."))
    return FILE_TYPES[extension]
