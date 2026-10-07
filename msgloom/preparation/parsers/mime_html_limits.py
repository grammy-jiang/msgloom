"""Shared finite budgets for the synchronous MIME/HTML parser."""

from __future__ import annotations

from dataclasses import dataclass, field

from msgloom.preparation.contracts import (
    BlockRole,
    LimitationKind,
    LinkBlock,
    MimePartReference,
    ParsedBlock,
    ParsedLink,
    ParsedTable,
    ParserLimitation,
    ParserLimits,
    SourceLocation,
    TableBlock,
    TextBlock,
)


@dataclass(slots=True)
class ExtractionState:
    """
    Accumulate bounded parser output in deterministic source order.

    The decompressed-byte limit bounds decoded source payload. The output-byte
    limit bounds source-derived strings emitted by this parser; the isolation
    codec later applies the exact serialized-output ceiling including
    provenance. The member limit bounds MIME and HTML structural traversal.
    """

    limits: ParserLimits
    decoded_bytes: int = 0
    output_bytes: int = 0
    members: int = 0
    blocks: list[ParsedBlock] = field(default_factory=list)
    mime_parts: list[MimePartReference] = field(default_factory=list)
    limitations: list[ParserLimitation] = field(default_factory=list)
    _limitation_keys: set[tuple[str, str]] = field(default_factory=set)

    def add_limitation(
        self,
        kind: LimitationKind,
        code: str,
        detail: str,
        *,
        feature: str | None = None,
        location: SourceLocation | None = None,
    ) -> None:
        """Add a safe, deduplicated limitation without source-body text."""
        key = (code, repr(location))
        if key in self._limitation_keys:
            return
        self._limitation_keys.add(key)
        self.limitations.append(
            ParserLimitation(
                kind=kind,
                code=code,
                detail=detail,
                feature=feature,
                location=location,
            )
        )

    def consume_member(self, *, location: SourceLocation | None = None) -> bool:
        """Reserve one structural member or record a partial-limit result."""
        if self.members >= self.limits.container_members:
            self.add_limitation(
                LimitationKind.PARTIAL,
                "container-member-limit",
                "Structural member limit reached; remaining content was skipped.",
                feature="container-members",
                location=location,
            )
            return False
        self.members += 1
        return True

    def consume_decoded(
        self,
        byte_count: int,
        *,
        location: SourceLocation | None = None,
    ) -> bool:
        """Reserve decoded source bytes before constructing readable output."""
        if self.decoded_bytes + byte_count > self.limits.decompressed_bytes:
            self.add_limitation(
                LimitationKind.PARTIAL,
                "decoded-bytes-limit",
                "Decoded-byte limit reached; affected readable content was skipped.",
                feature="decoded-bytes",
                location=location,
            )
            return False
        self.decoded_bytes += byte_count
        return True

    def reserve_output(
        self,
        *values: str | None,
        location: SourceLocation | None = None,
    ) -> bool:
        """Reserve UTF-8 source-derived output strings before emission."""
        required = sum(
            len(value.encode("utf-8")) for value in values if value is not None
        )
        if self.output_bytes + required > self.limits.output_bytes:
            self.add_limitation(
                LimitationKind.PARTIAL,
                "output-bytes-limit",
                "Semantic output limit reached; affected content was skipped.",
                feature="output-bytes",
                location=location,
            )
            return False
        self.output_bytes += required
        return True

    def add_text(
        self,
        role: BlockRole,
        text: str,
        location: SourceLocation,
        *,
        links: tuple[ParsedLink, ...] = (),
    ) -> None:
        """Append one text block if source-derived strings fit the budget."""
        values: list[str | None] = [text]
        for link in links:
            values.extend((link.target, link.text))
        if not self.reserve_output(*values, location=location):
            return
        self.blocks.append(
            TextBlock(
                order=len(self.blocks),
                role=role,
                text=text,
                location=location,
                links=links,
            )
        )

    def add_link(self, link: ParsedLink) -> None:
        """Append one standalone inert link under the output budget."""
        if not self.reserve_output(
            link.target,
            link.text,
            location=link.location,
        ):
            return
        self.blocks.append(LinkBlock(order=len(self.blocks), link=link))

    def add_table(self, table: ParsedTable) -> None:
        """Append a complete table or skip it rather than silently truncate."""
        values: list[str | None] = []
        for cell in table.cells:
            values.append(cell.text)
            for link in cell.links:
                values.extend((link.target, link.text))
        if not self.reserve_output(*values, location=table.location):
            return
        self.blocks.append(TableBlock(order=len(self.blocks), table=table))

    def add_mime_part(self, part: MimePartReference) -> bool:
        """Append MIME metadata when source fields fit output limits."""
        if not self.reserve_output(
            part.part_ref,
            part.parent_ref,
            part.content_type,
            part.disposition,
            part.content_id,
            location=part.location,
        ):
            return False
        self.mime_parts.append(part)
        return True
