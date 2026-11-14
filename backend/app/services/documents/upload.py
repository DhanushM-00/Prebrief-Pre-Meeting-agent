"""Secure file storage helpers — files never under a public web root."""
from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

from app.config import Settings
from app.services.documents.validation import sanitize_filename


def user_upload_dir(settings: Settings, user_id: str) -> Path:
    """Per-user directory under upload_dir. Creates if missing."""
    # Guard against path traversal in user_id
    safe_uid = "".join(c for c in user_id if c.isalnum() or c in "-_")
    if not safe_uid or safe_uid != user_id:
        raise ValueError("Invalid user id for storage path.")
    root = Path(settings.upload_dir).resolve()
    path = (root / safe_uid).resolve()
    if not str(path).startswith(str(root)):
        raise ValueError("Path traversal blocked.")
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_stored_filename(original: str, extension: str) -> str:
    safe = sanitize_filename(original)
    stem = safe.rsplit(".", 1)[0][:40] if "." in safe else safe[:40]
    token = secrets.token_hex(8)
    return f"{stem}_{token}.{extension}"


def save_bytes(
    settings: Settings,
    user_id: str,
    original_filename: str,
    extension: str,
    data: bytes,
) -> tuple[str, str, str]:
    """
    Write file to disk. Returns (stored_filename, relative_storage_path, content_hash).
    relative path is user_id/stored_filename (never absolute).
    """
    directory = user_upload_dir(settings, user_id)
    stored = make_stored_filename(original_filename, extension)
    full = (directory / stored).resolve()
    root = Path(settings.upload_dir).resolve()
    if not str(full).startswith(str(root)):
        raise ValueError("Path traversal blocked.")
    full.write_bytes(data)
    content_hash = hashlib.sha256(data).hexdigest()
    rel = f"{user_id}/{stored}"
    return stored, rel, content_hash


def resolve_storage_path(settings: Settings, storage_path: str) -> Path:
    """Resolve a relative storage_path to absolute, with traversal checks."""
    root = Path(settings.upload_dir).resolve()
    # Normalize and reject .. components
    parts = Path(storage_path).parts
    if ".." in parts or storage_path.startswith(("/", "\\")):
        raise ValueError("Invalid storage path.")
    full = (root / storage_path).resolve()
    if not str(full).startswith(str(root)):
        raise ValueError("Path traversal blocked.")
    return full


def delete_document_files(settings: Settings, storage_path: str) -> None:
    try:
        path = resolve_storage_path(settings, storage_path)
        if path.is_file():
            path.unlink()
    except Exception:
        pass


# Alias for package exports
save_upload = save_bytes

