"""Deterministic bounded logical BODY projection tests."""

from __future__ import annotations

import pytest


def _module():
    from message_ingest.acquisition.microsoft.outlook.email import rule_body

    return rule_body


def test_text_body_is_preserved_exactly() -> None:
    content = "  first line\nsecond\tline  "

    actual = _module().logical_mail_body({"contentType": "text", "content": content})

    if actual != content:
        pytest.fail("Text BODY projection rewrote provider text")


def test_html_collapses_normal_whitespace_and_keeps_block_br_boundaries() -> None:
    actual = _module().logical_mail_body(
        {
            "contentType": "html",
            "content": (
                "<div>Hello   <span>world</span><br>again</div>"
                "<p>Second\n paragraph</p>"
            ),
        }
    )

    if actual != "Hello world\nagain\nSecond paragraph":
        pytest.fail(f"HTML logical text boundary semantics changed: {actual!r}")


def test_html_active_elements_are_omitted() -> None:
    html = (
        "<div>visible"
        "<script>PRIVATE_SCRIPT</script>"
        "<style>PRIVATE_STYLE</style>"
        "<noscript>PRIVATE_NOSCRIPT</noscript>"
        "<template>PRIVATE_TEMPLATE</template>"
        "<iframe>PRIVATE_IFRAME</iframe>"
        "<object>PRIVATE_OBJECT</object>"
        '<embed src="private-embed.bin">'
        " end</div>"
    )

    actual = _module().logical_mail_body({"contentType": "html", "content": html})

    if actual != "visible end":
        pytest.fail(f"Active HTML leaked into logical body: {actual!r}")


def test_html_table_text_is_retained() -> None:
    actual = _module().logical_mail_body(
        {
            "contentType": "html",
            "content": (
                "<table><tr><th>Name</th><th>Value</th></tr>"
                "<tr><td>Alpha</td><td>42</td></tr></table>"
            ),
        }
    )

    for expected in ("Name", "Value", "Alpha", "42"):
        if expected not in actual:
            pytest.fail(f"Table text was dropped from logical BODY: {expected!r}")


def test_html_preformatted_text_preserves_whitespace() -> None:
    actual = _module().logical_mail_body(
        {
            "contentType": "html",
            "content": "<div>Before</div><pre>  alpha\n    beta\tend</pre><div>After</div>",
        }
    )

    if "  alpha\n    beta\tend" not in actual:
        pytest.fail(f"Preformatted whitespace was collapsed: {actual!r}")
    if not actual.startswith("Before\n") or not actual.endswith("\nAfter"):
        pytest.fail(f"Pre block boundaries changed: {actual!r}")


def test_preformatted_text_preserves_trailing_newline() -> None:
    actual = _module().logical_mail_body(
        {
            "contentType": "html",
            "content": "<pre>  alpha\n</pre>",
        }
    )

    if actual != "  alpha\n":
        pytest.fail(f"Preformatted trailing whitespace was changed: {actual!r}")


def test_html_entities_decode_deterministically() -> None:
    actual = _module().logical_mail_body(
        {"contentType": "html", "content": "<p>A &amp; B &lt; C&nbsp;D</p>"}
    )

    if actual != "A & B < C D":
        pytest.fail(f"HTML entity projection changed: {actual!r}")


@pytest.mark.parametrize(
    "body",
    (
        None,
        {},
        {"contentType": "text"},
        {"contentType": "text", "content": 123},
        {"contentType": "binary", "content": "private"},
        {"contentType": 123, "content": "private"},
    ),
)
def test_malformed_or_unsupported_body_is_unavailable(body: object) -> None:
    module = _module()

    with pytest.raises(module.MailBodyUnavailable):
        module.logical_mail_body(body)


def test_text_body_over_8_mib_utf8_is_unavailable() -> None:
    module = _module()
    content = "x" * (module.MAX_LOGICAL_BODY_BYTES + 1)

    with pytest.raises(module.MailBodyUnavailable) as caught:
        module.logical_mail_body({"contentType": "text", "content": content})

    if caught.value.reason_code != "body_too_large":
        pytest.fail("Oversized BODY used the wrong bounded reason")


def test_projected_html_body_over_8_mib_utf8_is_unavailable() -> None:
    module = _module()
    content = "<p>" + ("é" * (module.MAX_LOGICAL_BODY_BYTES // 2 + 1)) + "</p>"

    with pytest.raises(module.MailBodyUnavailable) as caught:
        module.logical_mail_body({"contentType": "html", "content": content})

    if caught.value.reason_code != "body_too_large":
        pytest.fail("Oversized projected BODY used the wrong bounded reason")


def test_private_body_content_never_appears_in_unavailable_error() -> None:
    module = _module()
    private = "PRIVATE_MAIL_BODY_913"

    with pytest.raises(module.MailBodyUnavailable) as caught:
        module.logical_mail_body({"contentType": "unsupported", "content": private})

    if private in str(caught.value) or private in repr(caught.value):
        pytest.fail("Mail BODY failure exposed private content")


def test_body_limit_constant_is_fixed() -> None:
    if _module().MAX_LOGICAL_BODY_BYTES != 8 * 1024 * 1024:
        pytest.fail("Logical BODY byte budget changed")
