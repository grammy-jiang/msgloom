"""Exact-str and control-character rules shared by every A2 v2 model."""

from __future__ import annotations

from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    has_control_character,
)
from msgloom.a2_kedro.contracts.extract import (
    ComponentEntry,
    ExtractedComponents,
    decode_metadata,
    encode_metadata,
)
from msgloom.a2_kedro.contracts.header import StageHeader
from msgloom.a2_kedro.contracts.held import HeldReason, InputDisposition
from msgloom.a2_kedro.contracts.relations import NativeRelations, NodeRef
from msgloom.a2_kedro.contracts.transition import TransitionItem
from msgloom.contracts import ResultRef
from tests.a2_kedro.helpers import check, hexd, transition_for


class FakeStr(str):
    """A ``str`` subclass that strict pydantic would silently normalize."""


#: One character for each forbidden class, named for the test id.
CONTROLS = {
    "nul": "\x00",
    "tab": "\t",
    "newline": "\n",
    "carriage_return": "\r",
    "escape": "\x1b",
    "del": "\x7f",
    "c1_start": "\x80",
    "next_line": "\x85",
    "c1_end": "\x9f",
    "line_separator": "\u2028",
    "paragraph_separator": "\u2029",
}
CONTROL_PARAMS = list(CONTROLS.values())
CONTROL_IDS = list(CONTROLS)


class Sample(A2Model):
    """Minimal model for base-class rules."""

    name: str
    pairs: tuple[tuple[str, str], ...] = ()
    ref: ResultRef | None = None


def comp(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "component_id": "p",
        "role": "primary",
        "status": "present",
        "reference": "saved/p",
        "sha256": hexd("a"),
    }
    return {**base, **kw}


def node(node_id: str = "a") -> dict[str, str]:
    return {"scope_kind": "thread", "scope_id": "t1", "node_id": node_id}


def test_plain_text_still_passes() -> None:
    value = Sample(name="ok é 中", pairs=(("k", "v"),))
    check(value.name.startswith("ok"), "plain text is accepted")


def test_has_control_character_classes() -> None:
    check(not has_control_character("plain é 中"), "plain text")
    for char in CONTROL_PARAMS:
        check(has_control_character("a" + char + "b"), repr(char))


def test_str_subclass_is_rejected_at_top_level_and_nested() -> None:
    with pytest.raises(ValueError):
        Sample(name=FakeStr("x"))
    with pytest.raises(ValueError):
        Sample(name="x", pairs=((FakeStr("k"), "v"),))
    with pytest.raises(ValueError):
        Sample(name="x", pairs=(("k", FakeStr("v")),))


def test_str_subclass_is_rejected_inside_a_dataclass_value() -> None:
    with pytest.raises(ValueError):
        Sample(name="x", ref=ResultRef(FakeStr("r"), "kind", "1"))
    with pytest.raises(ValueError):
        Sample(name="x", ref=ResultRef("r\x00", "kind", "1"))


def test_str_subclass_is_rejected_in_contract_models() -> None:
    with pytest.raises(ValueError):
        ComponentEntry.model_validate(comp(component_id=FakeStr("p")))
    with pytest.raises(ValueError):
        ComponentEntry.model_validate(comp(reference=FakeStr("saved/p")))
    with pytest.raises(ValueError):
        ComponentEntry.model_validate(comp(sha256=FakeStr(hexd("a"))))
    with pytest.raises(ValueError):
        ComponentEntry.model_validate(comp(role=FakeStr("primary")))
    with pytest.raises(ValueError):
        StageHeader(kind=FakeStr("zones"), version="1")
    with pytest.raises(ValueError):
        NodeRef(scope_kind="thread", scope_id=FakeStr("t"), node_id="a")
    with pytest.raises(ValueError):
        NodeRef.model_validate(
            {"scope_kind": FakeStr("thread"), "scope_id": "t", "node_id": "a"}
        )
    base = TransitionItem.from_intake(0, transition_for(1, "a"), "auth-1")
    with pytest.raises(ValueError):
        TransitionItem.model_validate(
            {**base.model_dump(), "authority": FakeStr("auth-1")}
        )


def test_str_enum_member_is_accepted_only_for_an_enum_field() -> None:
    check(HeldReason("proof_missing") is HeldReason.PROOF_MISSING, "enum")
    fields = InputDisposition.model_fields
    check(fields["reason"].annotation is HeldReason, "reason is an enum")
    with pytest.raises(ValueError):
        Sample(name=HeldReason.PROOF_MISSING)


@pytest.mark.parametrize("char", CONTROL_PARAMS, ids=CONTROL_IDS)
def test_control_character_is_rejected_in_models(char: str) -> None:
    with pytest.raises(ValueError):
        Sample(name="a" + char + "b")
    with pytest.raises(ValueError):
        Sample(name="x", pairs=(("k", "a" + char),))
    with pytest.raises(ValueError):
        ComponentEntry.model_validate(comp(component_id="p" + char))
    with pytest.raises(ValueError):
        ComponentEntry.model_validate(comp(reference="saved/" + char))
    with pytest.raises(ValueError):
        ComponentEntry.model_validate(comp(metadata=(("k", "v" + char),)))
    with pytest.raises(ValueError):
        ComponentEntry.model_validate(comp(metadata=(("k" + char, "v"),)))
    with pytest.raises(ValueError):
        NodeRef(scope_kind="thread", scope_id="t" + char, node_id="a")
    with pytest.raises(ValueError):
        NodeRef(scope_kind="thread", scope_id="t", node_id=char + "a")
    with pytest.raises(ValueError):
        NativeRelations.model_validate(
            {
                "nodes": (node("a"), node("b")),
                "relations": (
                    {
                        "kind": "reference",
                        "source": node("a"),
                        "target": node("b"),
                        "basis": "hdr" + char,
                    },
                ),
            }
        )
    base = TransitionItem.from_intake(0, transition_for(1, "a"), "auth-1")
    with pytest.raises(ValueError):
        TransitionItem.model_validate({**base.model_dump(), "authority": "auth" + char})
    with pytest.raises(ValueError):
        TransitionItem.model_validate({**base.model_dump(), "scope_id": char})


@pytest.mark.parametrize("char", CONTROL_PARAMS, ids=CONTROL_IDS)
def test_control_character_is_rejected_by_the_metadata_codec(char: str) -> None:
    with pytest.raises(A2ContractError):
        encode_metadata({"k": "v" + char})
    with pytest.raises(A2ContractError):
        encode_metadata({"k" + char: "v"})
    escaped = f'{{"k":"v\\u{ord(char):04x}"}}'
    with pytest.raises(A2ContractError):
        decode_metadata(escaped.encode())


def test_metadata_codec_rejects_str_subclass() -> None:
    with pytest.raises(A2ContractError):
        encode_metadata({"k": FakeStr("v")})
    with pytest.raises(A2ContractError):
        encode_metadata({FakeStr("k"): "v"})


def test_control_character_is_rejected_on_decode() -> None:
    good = ExtractedComponents.model_validate({"components": (comp(),)})
    data = good.encode()
    check(ExtractedComponents.decode(data) == good, "baseline decodes")
    bad = data.replace(b"saved/p", b"saved/\\u0000p")
    with pytest.raises(A2ContractError):
        ExtractedComponents.decode(bad)
    bad = data.replace(b"saved/p", b"saved/\\u2028p")
    with pytest.raises(A2ContractError):
        ExtractedComponents.decode(bad)


def test_non_ascii_printable_text_is_kept_byte_exact() -> None:
    value = ExtractedComponents.model_validate(
        {"components": (comp(reference="saved/é中"),)}
    )
    check(ExtractedComponents.decode(value.encode()) == value, "round trip")
