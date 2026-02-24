"""
Utility functions for multiagent-firewall.

This package is organized into:
- core: Debug utilities and state management
- validation: File validation and security functions
- exceptions: Custom exception classes
"""

from __future__ import annotations

# Import from submodules
from .core import append_error, append_warning, debug_ainvoke
from .exceptions import FileValidationError
from .validation import (
    sanitize_filename,
    validate_file_size,
    validate_mime_type,
    validate_path_traversal,
)

# Backward compatibility - export everything at package level
__all__ = [
    # Core utilities
    "debug_ainvoke",
    "append_error",
    "append_warning",
    # Validation utilities
    "FileValidationError",
    "validate_file_size",
    "validate_mime_type",
    "sanitize_filename",
    "validate_path_traversal",
]
