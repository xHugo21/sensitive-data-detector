import logging
import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, Tuple, Dict, Any

from app.utils import debug_log
from multiagent_firewall import GuardOrchestrator
from multiagent_firewall.config import FILE_TYPE_CONFIG
from multiagent_firewall.utils import (
    FileValidationError,
    sanitize_filename,
    validate_file_size,
    validate_mime_type,
    validate_path_traversal,
)
from app.config import GUARD_CONFIG, DEFAULT_BLOCK_LEVEL

logger = logging.getLogger(__name__)
router = APIRouter()

# Constants
MAX_SNIPPET_LENGTH = 400  # Characters to include in response


async def _validate_and_save_uploaded_file(
    file: UploadFile,
) -> Tuple[Path, Dict[str, Any]]:
    """
    Validate file security and save to temporary directory.

    Performs comprehensive security validation:
    - File size limits (streaming to prevent memory exhaustion)
    - Path traversal protection (cryptographic random filenames)
    - Extension validation (allowlist approach)
    - MIME type validation (magic number detection)

    Args:
        file: Uploaded file from FastAPI

    Returns:
        Tuple of (file_path, metadata_dict) where metadata contains:
        - file_size_bytes: Size of uploaded file
        - original_filename: Original filename from upload

    Raises:
        HTTPException: For any validation failures (400, 413)
    """
    tmp_dir = Path(tempfile.gettempdir())

    # Generate secure random filename
    safe_filename_str = sanitize_filename(file.filename)
    tmp_path = tmp_dir / safe_filename_str

    # Validate no path traversal
    try:
        validate_path_traversal(tmp_path, tmp_dir)
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail="Invalid file path")

    # Stream file with global size limit (50MB)
    max_size = FILE_TYPE_CONFIG.global_max_size_bytes
    chunk_size = FILE_TYPE_CONFIG.chunk_size_bytes
    file_size = 0

    try:
        with open(tmp_path, "wb") as f:
            while chunk := await file.read(chunk_size):
                file_size += len(chunk)
                if file_size > max_size:
                    # Cleanup partial file
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass

                    max_mb = max_size / (1024 * 1024)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {max_mb:.0f}MB",
                    )
                f.write(chunk)

        debug_log(
            f"[SensitiveDataDetectorBackend] Saved file to {tmp_path} ({file_size} bytes)"
        )

        # Validate file type by extension
        file_type_def = FILE_TYPE_CONFIG.get_by_extension(file.filename or "")
        if not file_type_def:
            tmp_path.unlink()
            ext = Path(file.filename or "").suffix or "(no extension)"
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}",
            )

        # Validate MIME type
        if FILE_TYPE_CONFIG.require_mime_validation:
            try:
                detected_mime = validate_mime_type(tmp_path, file_type_def.mime_types)
                debug_log(
                    f"[SensitiveDataDetectorBackend] Detected MIME: {detected_mime}"
                )
            except FileValidationError as e:
                tmp_path.unlink()
                # Don't expose internal validation details
                raise HTTPException(
                    status_code=400,
                    detail="File validation failed: invalid file format",
                )

        # Return path and metadata
        metadata = {
            "file_size_bytes": file_size,
            "original_filename": file.filename,
        }
        return tmp_path, metadata

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Cleanup on unexpected errors
        try:
            tmp_path.unlink()
        except OSError:
            pass
        logger.exception(f"Unexpected error saving file: {file.filename}")
        raise HTTPException(status_code=500, detail="File processing failed")


@router.post("/detect")
async def detect(
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    min_block_level: Optional[str] = Form(None),
):
    """
    Unified detection endpoint with security hardening.

    Security features:
    - File size validation (50MB global limit)
    - MIME type validation via filetype library
    - Path traversal protection
    - Secure random filenames
    - Streaming upload (prevents memory exhaustion)

    Args:
        text: Direct text input
        file: File upload (PDF, images, text, code files)
        min_block_level: Minimum risk level to trigger blocking actions

    Returns:
        Detection results with risk level, detected fields, and remediation
    """
    try:
        block_level = min_block_level or DEFAULT_BLOCK_LEVEL

        if not text and not file:
            raise HTTPException(
                status_code=400, detail="Either text or file must be provided"
            )

        # Handle file upload with security checks
        if file:
            tmp_path, metadata = await _validate_and_save_uploaded_file(file)

            try:
                # Process file
                result = await GuardOrchestrator(GUARD_CONFIG).run(
                    file_path=str(tmp_path),
                    min_block_level=block_level,
                )

                # Add metadata
                if result.get("raw_text"):
                    result["extracted_snippet"] = result["raw_text"][
                        :MAX_SNIPPET_LENGTH
                    ]
                result.update(metadata)

                return result

            finally:
                # Cleanup temp file with proper error handling
                try:
                    tmp_path.unlink()
                except FileNotFoundError:
                    pass  # Already deleted
                except OSError as e:
                    logger.warning(f"Failed to cleanup temp file: {e}")

        # Handle text input
        debug_log("[SensitiveDataDetectorBackend] Processing text:", text)
        result = await GuardOrchestrator(GUARD_CONFIG).run(
            text=text,
            min_block_level=block_level,
        )

        debug_log(
            "[SensitiveDataDetectorBackend] Detected fields:",
            result.get("detected_fields", []),
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /detect")
        raise HTTPException(status_code=500, detail="Internal server error")
