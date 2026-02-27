"""Credential resolution helpers for RSS-to-Twitter Agent (Hive v0.6+)."""

from __future__ import annotations

import os
from pathlib import Path


def _parse_credential_ref(ref: str | None) -> tuple[str, str] | None:
    if not ref or "/" not in ref:
        return None
    name, alias = ref.split("/", 1)
    name = name.strip()
    alias = alias.strip()
    if not name or not alias:
        return None
    return name, alias


def resolve_twitter_session_dir(credential_ref: str | None = None) -> str | None:
    """Resolve session directory from env or Hive credential {name}/{alias} ref."""
    from_env = os.environ.get("HIVE_TWITTER_SESSION_DIR")
    if from_env:
        return str(Path(from_env).expanduser())

    effective_ref = credential_ref or os.environ.get("TWITTER_CREDENTIAL_REF")
    parsed = _parse_credential_ref(effective_ref)
    if not parsed:
        return None

    name, alias = parsed
    try:
        from framework.credentials.store import CredentialStore
    except Exception:
        return None

    base_path = os.environ.get("HIVE_CREDENTIALS_PATH")
    store = CredentialStore.with_encrypted_storage(base_path=base_path)
    credential = store.get_credential(effective_ref, refresh_if_needed=True)
    if credential is None:
        credential = store.get_credential_by_alias(name, alias)
    if credential is None:
        return None

    for key_name in ("session_dir", "user_data_dir", "playwright_session_dir", "path"):
        try:
            value = credential.get_key(key_name)
        except Exception:
            value = None
        if value:
            resolved = str(Path(value).expanduser())
            os.environ["HIVE_TWITTER_SESSION_DIR"] = resolved
            return resolved
    return None

