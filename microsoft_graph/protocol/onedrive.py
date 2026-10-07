"""Pure OneDrive response mechanics without acquisition reset policy."""

from collections.abc import Sequence
from urllib.parse import urlsplit


def onedrive_resync_location(
    raw_locations: Sequence[bytes | str], *, graph_root: str
) -> str | None:
    """
    Return one exact same-origin Graph Location without normalizing it.

    Read the raw Location header values without a transport dependency.
    Missing, ambiguous, or unsafe locations return ``None``. The caller owns
    status handling and reset-attempt policy; no URL is requested here.
    """
    if len(raw_locations) != 1:
        return None
    raw_location = raw_locations[0]
    location = (
        raw_location.decode("latin-1")
        if isinstance(raw_location, bytes)
        else raw_location
    )
    if not location or location != location.strip():
        return None
    try:
        candidate = urlsplit(location)
        root = urlsplit(graph_root)
        candidate_port = candidate.port or (443 if candidate.scheme == "https" else 80)
        root_port = root.port or (443 if root.scheme == "https" else 80)
    except ValueError:
        return None
    if (
        candidate.scheme.lower() != root.scheme.lower()
        or candidate.hostname != root.hostname
        or candidate_port != root_port
        or candidate.username is not None
        or candidate.password is not None
        or candidate.fragment
    ):
        return None
    return location
