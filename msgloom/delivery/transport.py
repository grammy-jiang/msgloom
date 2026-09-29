"""Narrow async transport contracts and one-shot Microsoft Graph adapter."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote

from msgloom.contracts import ExternalEffectState


@dataclass(frozen=True, slots=True)
class TransportReceipt:
    """Provider-neutral result of exactly one external submission call."""

    effect: ExternalEffectState
    provider_status: str
    provider_receipt: str | None = None

    def __post_init__(self) -> None:
        if self.effect not in {
            ExternalEffectState.ACCEPTED,
            ExternalEffectState.CONFIRMED,
            ExternalEffectState.REJECTED,
        }:
            raise ValueError("transport receipt must be definite")
        if not self.provider_status.strip():
            raise ValueError("provider status must be non-empty")


class ReportTransport(Protocol):
    """Submit exact already-persisted bytes once, with no implicit retry."""

    async def submit(
        self, send_bytes: bytes, *, timeout_seconds: float
    ) -> TransportReceipt:
        """Submit exact bytes once and return a definite provider response."""
        ...


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Bounded response metadata from one explicitly injected HTTP call."""

    status_code: int
    request_id: str | None = None


class OneShotHttpTransport(Protocol):
    """Execute one HTTP POST without redirects or automatic retries."""

    async def post(
        self,
        url: str,
        *,
        headers: tuple[tuple[str, str], ...],
        body: bytes,
        timeout_seconds: float,
        allow_redirects: bool,
        retries: int,
    ) -> HttpResponse:
        """Execute exactly one bounded POST."""
        ...


class GraphSendMailTransport:
    """Send deterministic MIME through Graph v1.0 using injected HTTP only."""

    def __init__(
        self,
        *,
        mailbox: str,
        bearer_token: str,
        http: OneShotHttpTransport,
    ) -> None:
        if not mailbox or any(char in mailbox for char in ("\r", "\n", "/", "?")):
            raise ValueError("Graph mailbox identity is invalid")
        if not bearer_token or any(char in bearer_token for char in ("\r", "\n")):
            raise ValueError("Graph bearer token is invalid")
        self._url = (
            "https://graph.microsoft.com/v1.0/users/"
            f"{quote(mailbox, safe='@.-_')}/sendMail"
        )
        self._token = bearer_token
        self._http = http

    async def submit(
        self, send_bytes: bytes, *, timeout_seconds: float
    ) -> TransportReceipt:
        """POST base64 MIME once; Graph 202 means accepted, not delivered."""
        response = await self._http.post(
            self._url,
            headers=(
                ("Authorization", f"Bearer {self._token}"),
                ("Content-Type", "text/plain"),
            ),
            body=base64.b64encode(send_bytes),
            timeout_seconds=timeout_seconds,
            allow_redirects=False,
            retries=0,
        )
        status = response.status_code
        if status == 202:
            return TransportReceipt(
                ExternalEffectState.ACCEPTED,
                "202",
                response.request_id,
            )
        if 400 <= status < 500 and status != 408 and status != 429:
            return TransportReceipt(
                ExternalEffectState.REJECTED,
                str(status),
                response.request_id,
            )
        raise RuntimeError("Graph submission outcome is not definitively classified")
