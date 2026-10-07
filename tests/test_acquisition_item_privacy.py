"""Keep exact acquisition evidence out of implicit diagnostic formatting."""

from dataclasses import asdict

import pytest

from message_ingest.items.acquisition import AcquisitionFailureItem, RawHttpEvidenceItem


@pytest.mark.parametrize("format_item", [repr, str])
def test_inbound_evidence_diagnostics_preserve_private_storage(format_item) -> None:
    """Notification secrets stay in evidence fields, never item diagnostics."""
    body = b'{"value":[{"clientState":"private-client-state"}]}'
    item = RawHttpEvidenceItem(
        evidence_id="a" * 32,
        run_id="run-1",
        purpose="inbound-notification",
        observed_at="2026-10-04T00:00:00Z",
        origin="inbound-webhook",
        request_fingerprint="inbound-capture",
        request_url="https://private-delivery.test/private-path",
        request_method="POST",
        request_headers={},
        request_body=body,
        response_url=None,
        response_status=None,
        response_headers={},
        response_body=b"",
        response_flags=[],
    )
    item.request_headers = {"Authorization": ["private-request-header"]}
    item.response_url = "https://private-response.test/private-path"
    item.response_headers = {"Set-Cookie": ["private-response-header"]}
    item.response_body = b"private-response-body"
    item.error_type = "private-error-type"
    item.error_message = "private-error-message"
    before = asdict(item)

    rendered = format_item(item)

    for value in (
        "private-client-state",
        "private-delivery",
        "private-request-header",
        "private-response",
        "private-error",
        "clientState",
    ):
        if value in rendered:
            pytest.fail("Private acquisition data escaped through item formatting")
    if asdict(item) != before or item.request_body != body:
        pytest.fail("Diagnostic privacy must preserve exact evidence fields")
    if item.evidence_id not in rendered:
        pytest.fail("Diagnostics should retain the evidence correlation ID")


@pytest.mark.parametrize("format_item", [repr, str])
def test_failure_diagnostics_preserve_private_storage(format_item) -> None:
    """Failure context and arbitrary exception values remain storage only."""
    item = AcquisitionFailureItem(
        url="https://private-resource.test/message",
        purpose="message-read",
        error_type="private-exception-type",
        error_message="private-exception-text",
        observed_at="2026-10-04T00:00:00Z",
        context={"resource": "private-resource-id"},
        evidence_id="evidence-1",
    )
    before = asdict(item)

    rendered = format_item(item)

    if "private-" in rendered:
        pytest.fail("Private failure data escaped through item formatting")
    if asdict(item) != before:
        pytest.fail("Diagnostic privacy must preserve exact failure fields")
    if item.evidence_id not in rendered:
        pytest.fail("Diagnostics should retain the evidence correlation ID")
