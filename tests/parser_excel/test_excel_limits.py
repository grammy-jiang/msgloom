"""Container, limit, identity, and closed-setting boundary regressions."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest

from msgloom.preparation.contracts import (
    DocumentFormat,
    LimitationKind,
    ParserIdentity,
)
from msgloom.preparation.parsers import excel as excel_parser
from msgloom.preparation.parsers.excel import parse
from tests.parser_excel.helpers import (
    build_ods_fixture,
    build_visibility_fixture,
    request_for,
)

_OLE_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")


def test_rejects_member_decompression_and_output_limit_overruns() -> None:
    content = build_visibility_fixture()

    with pytest.raises(ValueError, match="member ceiling"):
        parse(
            request_for(
                content,
                DocumentFormat.XLSX,
                container_members=1,
            ),
            content,
        )

    with ZipFile(BytesIO(content)) as archive:
        expanded = sum(info.file_size for info in archive.infolist())
    decompressed_limit = max(len(content), expanded - 1)
    if decompressed_limit >= expanded:
        pytest.fail("synthetic fixture did not provide compressed expansion")
    with pytest.raises(ValueError, match="decompressed member ceiling"):
        parse(
            request_for(
                content,
                DocumentFormat.XLSX,
                decompressed_bytes=decompressed_limit,
            ),
            content,
        )

    with pytest.raises(ValueError, match="output ceiling"):
        parse(
            request_for(
                content,
                DocumentFormat.XLSX,
                output_bytes=512,
            ),
            content,
        )


def test_native_password_signal_is_a_fatal_explicit_limitation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = build_visibility_fixture()
    request = request_for(content, DocumentFormat.XLSX)

    class PasswordWorkbook:
        @staticmethod
        def from_filelike(_: BytesIO):
            raise excel_parser.PasswordError("synthetic password signal")

    monkeypatch.setattr(excel_parser, "CalamineWorkbook", PasswordWorkbook)
    output = parse(request, content)

    if output.blocks:
        pytest.fail("password-protected workbook unexpectedly produced content")
    limitation = next(
        (item for item in output.limitations if item.kind is LimitationKind.ENCRYPTED),
        None,
    )
    if limitation is None or limitation.code != "excel-password-protected":
        pytest.fail("native password signal was not classified as encryption")


def test_malformed_signature_and_container_fail_before_native_parsing() -> None:
    malformed = b"not-a-spreadsheet"
    request = request_for(malformed, DocumentFormat.XLSX)
    with pytest.raises(ValueError, match="signature"):
        parse(request, malformed)

    truncated_zip = b"PK\x03\x04" + bytes(12)
    request = request_for(truncated_zip, DocumentFormat.XLSB)
    with pytest.raises(ValueError, match="malformed spreadsheet ZIP"):
        parse(request, truncated_zip)


def test_ods_requires_structural_mimetype_member_order() -> None:
    content = build_ods_fixture()
    source = ZipFile(BytesIO(content))
    buffer = BytesIO()
    try:
        with ZipFile(buffer, "w") as target:
            target.writestr(
                "content.xml",
                source.read("content.xml"),
                compress_type=ZIP_DEFLATED,
            )
            target.writestr(
                "mimetype",
                source.read("mimetype"),
                compress_type=ZIP_STORED,
            )
            target.writestr(
                "META-INF/manifest.xml",
                source.read("META-INF/manifest.xml"),
                compress_type=ZIP_DEFLATED,
            )
    finally:
        source.close()
    malformed = buffer.getvalue()

    with pytest.raises(ValueError, match="mimetype member must be first"):
        parse(request_for(malformed, DocumentFormat.ODS), malformed)


def test_closed_format_identity_and_setting_checks() -> None:
    content = build_visibility_fixture()

    pdf_request = request_for(content, DocumentFormat.PDF)
    with pytest.raises(ValueError, match="does not accept pdf"):
        parse(pdf_request, content)

    request = request_for(content, DocumentFormat.XLSX)
    wrong_identity = replace(
        request,
        parser=ParserIdentity(
            name="msgloom.excel",
            version="2",
            backend="wrong",
        ),
    )
    with pytest.raises(ValueError, match="identity"):
        parse(wrong_identity, content)

    unknown_setting = replace(
        request,
        config=replace(
            request.config,
            settings=(("network_access", "true"),),
        ),
    )
    with pytest.raises(ValueError, match="unsupported Excel parser settings"):
        parse(unknown_setting, content)

    invalid_boolean = replace(
        request,
        config=replace(
            request.config,
            settings=(("include_hidden_rows", "sometimes"),),
        ),
    )
    with pytest.raises(ValueError, match="explicit boolean"):
        parse(invalid_boolean, content)


def test_source_digest_and_byte_count_are_verified_before_parsing() -> None:
    content = build_visibility_fixture()
    request = request_for(content, DocumentFormat.XLSX)

    bad_count = replace(
        request,
        source=replace(
            request.source,
            byte_count=request.source.byte_count + 1,
        ),
    )
    with pytest.raises(ValueError, match="byte count"):
        parse(bad_count, content)

    bad_digest = replace(
        request,
        source=replace(request.source, sha256="0" * 64),
    )
    with pytest.raises(ValueError, match="digest"):
        parse(bad_digest, content)
