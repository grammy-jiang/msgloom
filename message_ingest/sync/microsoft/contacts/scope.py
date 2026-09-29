"""Contacts synchronization scope validation."""


def require_custom_folder_scope(folder_id: str) -> str:
    """Require a concrete provider folder identity for delta synchronization."""
    if not isinstance(folder_id, str) or not folder_id.strip():
        raise ValueError("Contacts delta requires a concrete custom-folder ID")
    return folder_id


__all__ = ["require_custom_folder_scope"]
