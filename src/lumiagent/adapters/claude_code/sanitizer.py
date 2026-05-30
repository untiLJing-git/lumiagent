"""Sanitization helpers for Claude Code fixtures and hook payloads."""
from __future__ import annotations

import re
from typing import Any

_SECRET_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
    "access_token",
}
_REDACTED = "[REDACTED]"
_SECRET_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[^\s]+"),
    re.compile(r"(?i)(token\s*=\s*)[^\s]+"),
    re.compile(r"(?i)(api[_-]?key\s*=\s*)[^\s]+"),
    re.compile(r"(?i)(password\s*[:=]\s*)[^\s]+"),
)


def sanitize_value(value: Any, *, project_root: str | None = None) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if _is_secret_key(key):
                sanitized[key] = _REDACTED
            else:
                sanitized[key] = sanitize_value(item, project_root=project_root)
        return sanitized
    if isinstance(value, list):
        return [sanitize_value(item, project_root=project_root) for item in value]
    if isinstance(value, str):
        return sanitize_text(_replace_project_root(value, project_root))
    return value


def sanitize_payload(payload: dict[str, Any], *, project_root: str | None = None) -> dict[str, Any]:
    sanitized = sanitize_value(payload, project_root=project_root)
    if isinstance(sanitized, dict):
        return sanitized
    return {}


def sanitize_text(text: str) -> str:
    sanitized = text
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub(lambda match: f"{match.group(1)}{_REDACTED}", sanitized)
    return sanitized


def _is_secret_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return (
        normalized in _SECRET_KEYS
        or normalized.endswith("_token")
        or normalized.endswith("_secret")
    )


def _replace_project_root(value: str, project_root: str | None) -> str:
    normalized = value.replace("\\", "/")
    if project_root is None:
        return normalized
    return normalized.replace(project_root.replace("\\", "/"), "<PROJECT_DIR>")
