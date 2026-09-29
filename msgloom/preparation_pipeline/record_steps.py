"""Prepared-record construction and isolated parser steps."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from msgloom.contracts import (
    Limitation,
    OperationRequest,
    ResultRef,
    TerminalStatus,
    VersionRef,
)
from msgloom.preparation import (
    DocumentFormat,
    DocumentLocation,
    FilteringDecision,
    FilteringDisposition,
    ParserOutput,
    ParserRequest,
    PreparedAttachment,
    PreparedRecord,
    ReferencedParserOutput,
    SavedByteReference,
    SourceMapping,
)
from msgloom.preparation.contracts import SourceLocation
from msgloom.preparation.isolation import parse_isolated
from msgloom.preparation.isolation.wire import encode_output
from msgloom.sources import CollectedBody, CollectedSourceReader

from ._state import CapturedSelection as _Captured
from ._state import RunState as _RunState
from .codec import (
    DERIVED_BYTES_KIND,
    DERIVED_BYTES_SCHEMA_VERSION,
    DerivedByteArtifact,
)
from .component_loading import load_selected_component
from .formatting import (
    attachment_format,
    format_for_kind,
    metadata_json,
    parsed_mappings,
    parser_limitations,
    primary_mapping,
    readable_text,
)
from .models import PreparationPlan
from .parsed_identity import parsed_version


class RecordSteps:
    """Build prepared records while retaining exact parser provenance."""

    _reader: CollectedSourceReader
    _plan: PreparationPlan
    _save_value: Callable[..., Awaitable[ResultRef]]
    _prepared_version: Callable[[PreparedRecord], Awaitable[VersionRef]]
    _run_sync_owned: Callable[..., Awaitable[Any]]

    async def _prepare_all(
        self,
        request: OperationRequest,
        captured: tuple[_Captured, ...],
        state: _RunState,
    ) -> tuple[
        tuple[PreparedRecord, ...],
        tuple[ResultRef, ...],
        tuple[VersionRef, ...],
    ]:
        records: list[PreparedRecord] = []
        refs: list[ResultRef] = []
        versions: list[VersionRef] = []
        for ordinal, item in enumerate(captured):
            ref_start = len(state.refs)
            record = await self._prepare_record(request, item, ordinal, state)
            derived_refs = tuple(
                ref for ref in state.refs[ref_start:] if ref.kind == "derived_bytes"
            )
            for limitation in record.limitations:
                if limitation not in state.limitations:
                    state.limitations.append(limitation)
            status = (
                TerminalStatus.INCOMPLETE
                if record.limitations
                else TerminalStatus.COMPLETE
            )
            prepared_version = await self._prepared_version(record)
            parser_sources = tuple(
                attachment.reference for attachment in record.attachments
            )
            ref = await self._save_value(
                request,
                state,
                "prepared",
                "1",
                record,
                source_versions=(record.source, *parser_sources),
                prepared_versions=(prepared_version,),
                input_refs=(item.result_ref, *derived_refs),
                tag=f"prepared:{ordinal}:{prepared_version.version}",
                status=status,
            )
            records.append(record)
            refs.append(ref)
            versions.append(prepared_version)
        return tuple(records), tuple(refs), tuple(versions)

    async def _prepare_record(
        self,
        request: OperationRequest,
        captured: _Captured,
        ordinal: int,
        state: _RunState,
    ) -> PreparedRecord:
        source = captured.selection.record
        state_start = len(state.limitations)
        limitations = list(source.limitations)
        parsed: list[ReferencedParserOutput] = []
        mappings: list[SourceMapping] = []
        if source.subject is not None:
            location = next(
                (
                    item
                    for item in source.source_locations
                    if isinstance(item, DocumentLocation)
                ),
                DocumentLocation(part="source"),
            )
            mappings.append(
                SourceMapping(source=source.source, field="subject", location=location)
            )

        body_text = source.body.content if source.body is not None else None
        if source.body is not None:
            limitations.extend(source.body.limitations)
            parsed_body = await self._parse_derived_body(
                request, captured, source.body, f"body:{ordinal}", state
            )
            if parsed_body is not None:
                parsed_ref, output = parsed_body
                parsed_index = len(parsed)
                parsed.append(
                    ReferencedParserOutput(reference=parsed_ref, output=output)
                )
                mappings.extend(parsed_mappings(parsed_ref, parsed_index, output))
                if source.body.kind.value != "plain":
                    body_text = readable_text(output)
                limitations.extend(parser_limitations(output))
            if body_text is not None:
                mapping = primary_mapping(source.source, "body", source.body.location)
                if mapping is not None:
                    mappings.append(mapping)
        for index, body in enumerate(source.alternate_bodies):
            limitations.extend(body.limitations)
            parsed_body = await self._parse_derived_body(
                request,
                captured,
                body,
                f"alternate-body:{ordinal}:{index}",
                state,
            )
            if parsed_body is not None:
                parsed_ref, output = parsed_body
                parsed_index = len(parsed)
                parsed.append(
                    ReferencedParserOutput(reference=parsed_ref, output=output)
                )
                mappings.extend(parsed_mappings(parsed_ref, parsed_index, output))
                limitations.extend(parser_limitations(output))
        metadata_output = await self._parse_derived_text(
            request,
            captured,
            metadata_json(source),
            DocumentLocation(part="collected-metadata"),
            DocumentFormat.JSON,
            f"metadata:{ordinal}",
            state,
        )
        if metadata_output is not None:
            parsed_ref, output = metadata_output
            parsed_index = len(parsed)
            parsed.append(ReferencedParserOutput(reference=parsed_ref, output=output))
            mappings.extend(parsed_mappings(parsed_ref, parsed_index, output))
            limitations.extend(parser_limitations(output))

        attachments: list[PreparedAttachment] = []
        for index, attachment in enumerate(source.attachments):
            item_limitations = list(attachment.limitations)
            parsed_ref: VersionRef | None = None
            if attachment.saved_bytes is None:
                item_limitations.append(
                    Limitation(
                        "missing-attachment-bytes",
                        "Attachment has no verified saved bytes for parsing.",
                    )
                )
            elif (format_ := attachment_format(attachment)) is None:
                item_limitations.append(
                    Limitation(
                        "unsupported-attachment-format",
                        "Attachment format is not supported by configured parsers.",
                    )
                )
            elif (profile := self._plan.profile_for(format_)) is None:
                item_limitations.append(
                    Limitation(
                        "parser-profile-unavailable",
                        "No trusted parser profile is configured for this format.",
                    )
                )
            else:
                content = await load_selected_component(
                    self._reader, attachment.saved_bytes, item_limitations
                )
                if content is not None:
                    output = await self._parse(
                        profile.format,
                        profile.parser,
                        profile.config,
                        profile.limits,
                        attachment.saved_bytes,
                        content,
                        state,
                    )
                    if output is not None:
                        parsed_ref = await parsed_version(
                            self._run_sync_owned,
                            captured,
                            f"attachment:{index}",
                            profile,
                            attachment.saved_bytes,
                            output,
                            configuration_version=self._plan.configuration_version,
                            code_version=self._plan.code_version,
                        )
                        parsed_index = len(parsed)
                        parsed.append(
                            ReferencedParserOutput(reference=parsed_ref, output=output)
                        )
                        mappings.extend(
                            parsed_mappings(attachment.reference, parsed_index, output)
                        )
                        item_limitations.extend(parser_limitations(output))
            attachments.append(
                PreparedAttachment(
                    reference=attachment.reference,
                    saved_bytes=attachment.saved_bytes,
                    parsed_content_ref=parsed_ref,
                    limitations=tuple(item_limitations),
                )
            )
            limitations.extend(item_limitations)

        limitations.extend(state.limitations[state_start:])

        return PreparedRecord(
            source=source.source,
            source_type=source.source_type,
            sender=source.sender,
            author=source.author,
            recipients=source.recipients,
            source_time=source.source_time,
            subject=source.subject,
            body=body_text,
            relationships=source.relationships,
            attachments=tuple(attachments),
            parsed_contents=tuple(parsed),
            limitations=tuple(limitations),
            source_mappings=tuple(mappings),
            filtering=FilteringDecision(disposition=FilteringDisposition.PENDING),
        )

    async def _parse_derived_body(
        self,
        request: OperationRequest,
        captured: _Captured,
        body: CollectedBody,
        component: str,
        state: _RunState,
    ) -> tuple[VersionRef, ParserOutput] | None:
        format_ = format_for_kind(body.kind)
        if (
            body.content is None
            and body.saved_bytes is not None
            and format_ is not None
        ):
            profile = self._plan.profile_for(format_)
            if profile is None:
                state.limitations.append(
                    Limitation(
                        "parser-profile-unavailable",
                        "No trusted parser profile is configured for selected content.",
                    )
                )
                return None
            content = await load_selected_component(
                self._reader, body.saved_bytes, state.limitations
            )
            if content is None:
                return None
            output = await self._parse(
                format_,
                profile.parser,
                profile.config,
                profile.limits,
                body.saved_bytes,
                content,
                state,
            )
            if output is None:
                return None
            return (
                await parsed_version(
                    self._run_sync_owned,
                    captured,
                    component,
                    profile,
                    body.saved_bytes,
                    output,
                    configuration_version=self._plan.configuration_version,
                    code_version=self._plan.code_version,
                ),
                output,
            )
        if body.content is None:
            state.limitations.append(
                Limitation(
                    "missing-body-content",
                    "Selected body has no parseable content or saved representation.",
                )
            )
            return None
        if format_ is None:
            state.limitations.append(
                Limitation(
                    "unsupported-body-format",
                    "Selected body representation has no supported parser.",
                )
            )
            return None
        return await self._parse_derived_text(
            request,
            captured,
            body.content,
            body.location,
            format_,
            component,
            state,
        )

    async def _parse_derived_text(
        self,
        request: OperationRequest,
        captured: _Captured,
        text: str,
        location: SourceLocation,
        format_: DocumentFormat,
        component: str,
        state: _RunState,
    ) -> tuple[VersionRef, ParserOutput] | None:
        profile = self._plan.profile_for(format_)
        if profile is None:
            state.limitations.append(
                Limitation(
                    "parser-profile-unavailable",
                    "No trusted parser profile is configured for selected content.",
                )
            )
            return None
        artifact = DerivedByteArtifact.capture(
            captured.selection.source,
            captured.selection.selection,
            component,
            location,
            text,
        )
        state.derived_bytes += artifact.byte_count
        if (
            artifact.byte_count > self._plan.max_derived_bytes
            or state.derived_bytes > self._plan.max_total_derived_bytes
        ):
            raise ValueError("derived parser input exceeds configured bound")
        await self._save_value(
            request,
            state,
            DERIVED_BYTES_KIND,
            DERIVED_BYTES_SCHEMA_VERSION,
            artifact,
            source_versions=(captured.selection.source,),
            input_refs=(captured.result_ref,),
            tag=f"derived:{component}:{artifact.sha256}",
        )
        saved = SavedByteReference(
            reference=artifact.stable_reference(),
            sha256=artifact.sha256,
            byte_count=artifact.byte_count,
        )
        output = await self._parse(
            format_,
            profile.parser,
            profile.config,
            profile.limits,
            saved,
            artifact.bytes(),
            state,
        )
        if output is None:
            return None
        return (
            await parsed_version(
                self._run_sync_owned,
                captured,
                component,
                profile,
                saved,
                output,
                configuration_version=self._plan.configuration_version,
                code_version=self._plan.code_version,
            ),
            output,
        )

    async def _parse(
        self,
        format_: DocumentFormat,
        parser,
        config,
        limits,
        saved: SavedByteReference,
        content: bytes,
        state: _RunState,
    ) -> ParserOutput | None:
        request = ParserRequest(
            source=saved,
            detected_format=format_,
            parser=parser,
            config=config,
            limits=limits,
        )
        try:
            output = await parse_isolated(request, content)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            state.limitations.append(
                Limitation(
                    "content-parse-failed",
                    "Content could not be parsed by the configured isolated parser.",
                )
            )
            return None
        encoded = await self._run_sync_owned(encode_output, output)
        state.parser_output_bytes += len(encoded)
        if state.parser_output_bytes > self._plan.max_total_parser_output_bytes:
            raise ValueError("aggregate parser output exceeds configured bound")
        return output
