"""File validation: extension, MIME, magic-byte signatures, size, path safety."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import Settings

# Magic-byte signatures (first bytes) for supported types
_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF", "pdf"),
    (b"PK\x03\x04", "zip"),  # docx / pptx / xlsx are ZIP containers
    (b"\xd0\xcf\x11\xe0", "ole"),  # legacy Office (reject)
]

_MIME_BY_EXT = {
    "pdf": {"application/pdf"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
    "pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/zip",
        "application/octet-stream",
    },
    "txt": {"text/plain", "application/octet-stream"},
    "csv": {"text/csv", "text/plain", "application/csv", "application/octet-stream"},
}

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class ValidationResult:
    ok: bool
    extension: str = ""
    content_type: str = ""
    error: str | None = None


def sanitize_filename(name: str) -> str:
    """Strip path components and dangerous characters; keep a short safe basename."""
    # Path traversal protection
    base = name.replace("\\", "/").split("/")[-1]
    base = base.lstrip(".")
    base = _SAFE_NAME_RE.sub("_", base)
    if not base or base in (".", ".."):
        base = "upload"
    return base[:200]


def validate_upload(
    *,
    filename: str,
    content_type: str | None,
    size: int,
    head_bytes: bytes,
    settings: Settings,
) -> ValidationResult:
    if size <= 0:
        return ValidationResult(ok=False, error="Empty file.")
    if size > settings.max_upload_bytes:
        mb = settings.max_upload_bytes // (1024 * 1024)
        return ValidationResult(ok=False, error=f"File exceeds maximum size of {mb} MB.")

    safe = sanitize_filename(filename)
    if "." not in safe:
        return ValidationResult(ok=False, error="File must have an extension.")
    ext = safe.rsplit(".", 1)[-1].lower()
    if ext not in settings.allowed_ext_set:
        allowed = ", ".join(sorted(settings.allowed_ext_set))
        return ValidationResult(ok=False, error=f"Unsupported file type. Allowed: {allowed}.")

    # Reject legacy OLE Office binaries
    if head_bytes.startswith(b"\xd0\xcf\x11\xe0"):
        return ValidationResult(ok=False, error="Legacy Office formats are not supported. Use DOCX/PPTX.")

    # Signature checks
    if ext == "pdf":
        if not head_bytes.startswith(b"%PDF"):
            return ValidationResult(ok=False, error="File does not look like a valid PDF.")
    elif ext in ("docx", "pptx"):
        if not head_bytes.startswith(b"PK\x03\x04"):
            return ValidationResult(ok=False, error=f"File does not look like a valid {ext.upper()}.")
    elif ext in ("txt", "csv"):
        # Reject binary-looking content
        sample = head_bytes[:4096]
        if b"\x00" in sample:
            return ValidationResult(ok=False, error="Text/CSV file contains binary data.")

    mime = (content_type or "application/octet-stream").split(";")[0].strip().lower()
    allowed_mimes = _MIME_BY_EXT.get(ext, set())
    if allowed_mimes and mime not in allowed_mimes and mime != "application/octet-stream":
        # Soft check — browsers often send wrong MIME; signature is authoritative
        pass

    return ValidationResult(ok=True, extension=ext, content_type=mime or "application/octet-stream")
