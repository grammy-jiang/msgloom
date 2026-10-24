"""Reference reader for the hand-written T0-08 historical reader oracle.

The reader is a small pure-Python model. Each named rule can be switched off,
so the mutation tests can show that the oracle needs the rule. It computes
nothing for A2 v2 and never imports ``msgloom``.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any

Case = dict[str, Any]
RULES = (
    "label_kind_exact", "label_version_exact", "v1_codec_strict",
    "unexpected_fields", "missing_fields", "canonical_defaults",
    "enum_and_text", "aware_time", "pending_no_rule", "parsed_refs_unique",
    "parsed_refs_dangling", "mapping_range", "v2_selection_valid",
    "v2_lineage_kinds", "v2_zone_range", "v2_status_consistency",
    "status_counts_all_sources", "projection_forbidden", "binding_line",
    "preserve_all_fields", "no_invented_fields", "limitations_all_sources",
    "limitation_order", "limitation_no_dedupe", "text_verbatim",
)  # fmt: skip
# Cases that must change when the rule is off. Written by hand.
SOURCE_TYPES = (
    "outlook_calendar", "outlook_email", "teams_channel_message",
    "teams_chat_message", "todo", "onedrive", "contact",
)  # fmt: skip
ROLES_V1 = ("to", "cc", "bcc", "member")
ROLES_V2 = ("primary", "component", "context", "transition")
ZONES = (
    "contribution",
    "quote_occurrence",
    "forward",
    "signature",
    "footer",
    "unknown",
)
RELATIONS = ("reply_parent", "ancestor", "quoted_source_hypothesis", "unknown")
DISPOSITIONS = ("pending", "included", "excluded")
LINEAGE = ("extracted_components", "parsed_parts", "zones", "native_relations")
V1_FIELDS = (
    "source", "source_type", "sender", "author", "recipients", "source_time",
    "subject", "body", "relationships", "attachments", "parsed_contents",
    "limitations", "source_mappings", "filtering",
)  # fmt: skip
V2_ONLY = ("selection", "role", "zones", "relations", "lineage", "completeness")
V2_FIELDS = tuple(f for f in V1_FIELDS if f != "filtering") + V2_ONLY
TIME_RE = re.compile(
    r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(Z|[+-]\d\d:\d\d)?"
)  # fmt: skip


# ------------------------------------------------------------- materialize ----


def _walk(node: Any, steps: list[str]) -> Any:
    for step in steps:
        node = node[int(step)] if isinstance(node, list) else node[step]
    return node


def materialize(stored: dict[str, Any], bases: dict[str, Any]) -> Any:
    """Return a deep copy of the base after the ordered edits."""
    payload = copy.deepcopy(bases[stored["base"]])
    for edit in stored["edits"]:
        steps = edit["path"].strip("/").split("/") if edit["path"] != "/" else []
        if edit["op"] == "copy":
            _walk(payload, steps).append(
                copy.deepcopy(_walk(payload, edit["from"].strip("/").split("/")))
            )
            continue
        parent = _walk(payload, steps[:-1])
        key: Any = int(steps[-1]) if isinstance(parent, list) else steps[-1]
        if edit["op"] == "delete":
            del parent[key]
        else:
            parent[key] = copy.deepcopy(edit["value"])
    return payload


# ---------------------------------------------------------------- reader ----


class Reject(Exception):
    """Carry the reason code of a refused record."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _check(rules: frozenset[str], rule: str, ok: bool, code: str) -> None:
    if rule in rules and not ok:
        raise Reject(code)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _span(start: Any, end: Any, limit: int | None) -> bool:
    """Return True for integers with 0 <= start < end (<= limit when given)."""
    if not (_is_int(start) and _is_int(end)):
        return False
    return 0 <= start < end and (limit is None or end <= limit)


def _shape(rules: frozenset[str], obj: Any, required: tuple[str, ...], defaulted: tuple[str, ...] = ()) -> dict[str, Any]:  # fmt: skip
    if not isinstance(obj, dict):
        raise Reject("bad_value")
    allowed = set(required) | set(defaulted)
    _check(rules, "unexpected_fields", set(obj) <= allowed, "unexpected_field")
    _check(rules, "missing_fields", set(required) <= set(obj), "missing_field")
    _check(rules, "canonical_defaults", set(defaulted) <= set(obj), "not_canonical")
    return obj


def _text(rules: frozenset[str], value: Any) -> None:
    ok = isinstance(value, str) and bool(value.strip())
    _check(rules, "enum_and_text", ok, "bad_value")


def _member(rules: frozenset[str], value: Any, allowed: tuple[str, ...]) -> None:
    _check(rules, "enum_and_text", value in allowed, "bad_value")


def _opt_text(rules: frozenset[str], value: Any) -> None:
    _check(rules, "enum_and_text", value is None or isinstance(value, str), "bad_value")


def _ref(rules: frozenset[str], value: Any) -> None:
    ref = _shape(rules, value, ("kind", "identity", "version"))
    for key in ("kind", "identity", "version"):
        _text(rules, ref.get(key))


def _party(rules: frozenset[str], value: Any) -> None:
    if value is None:
        return
    party = _shape(rules, value, ("identity",), ("display_name",))
    _text(rules, party.get("identity"))
    _opt_text(rules, party.get("display_name"))


def _limitations(rules: frozenset[str], items: Any) -> None:
    _check(rules, "enum_and_text", isinstance(items, list), "bad_value")
    for item in items if isinstance(items, list) else []:
        lim = _shape(rules, item, ("code", "detail"))
        _text(rules, lim.get("code"))
        _text(rules, lim.get("detail"))


def _parser_limitations(rules: frozenset[str], items: Any) -> None:
    """Check only the code of a parser limitation; its other keys are out of scope."""
    _check(rules, "enum_and_text", isinstance(items, list), "bad_value")
    for item in items if isinstance(items, list) else []:
        _check(rules, "enum_and_text", isinstance(item, dict), "bad_value")
        _text(rules, item.get("code"))


def _time(rules: frozenset[str], value: Any) -> None:
    match = TIME_RE.fullmatch(value) if isinstance(value, str) else None
    _check(rules, "enum_and_text", match is not None, "bad_value")
    _check(rules, "aware_time", match is None or match.group(1) is not None, "naive_time")  # fmt: skip


def _common(rules: frozenset[str], p: dict[str, Any]) -> None:
    _ref(rules, p.get("source"))
    _member(rules, p.get("source_type"), SOURCE_TYPES)
    _party(rules, p.get("sender"))
    _party(rules, p.get("author"))
    for rec in _list(rules, p.get("recipients")):
        item = _shape(rules, rec, ("party", "role"))
        _party(rules, item.get("party"))
        _member(rules, item.get("role"), ROLES_V1)
    _time(rules, p.get("source_time"))
    _opt_text(rules, p.get("subject"))
    _opt_text(rules, p.get("body"))
    for rel in _list(rules, p.get("relationships")):
        item = _shape(rules, rel, ("kind", "target"))
        _text(rules, item.get("kind"))
        _ref(rules, item.get("target"))
    for att in _list(rules, p.get("attachments")):
        item = _shape(rules, att, ("reference",), ("saved_bytes", "parsed_content_ref", "limitations"))  # fmt: skip
        _ref(rules, item.get("reference"))
        if item.get("parsed_content_ref") is not None:
            _ref(rules, item["parsed_content_ref"])
        _limitations(rules, item.get("limitations", []))
    parsed = []
    for content in _list(rules, p.get("parsed_contents")):
        item = _shape(rules, content, ("reference", "output"))
        _ref(rules, item.get("reference"))
        out = item.get("output")
        _check(rules, "enum_and_text", isinstance(out, dict), "bad_value")
        _parser_limitations(
            rules, out.get("limitations") if isinstance(out, dict) else None
        )
        parsed.append(json.dumps(item.get("reference"), sort_keys=True))
    _check(rules, "parsed_refs_unique", len(parsed) == len(set(parsed)), "duplicate_parsed_ref")  # fmt: skip
    for att in _list(rules, p.get("attachments")):
        ref = att.get("parsed_content_ref")
        known = ref is None or json.dumps(ref, sort_keys=True) in parsed
        _check(rules, "parsed_refs_dangling", known, "dangling_parsed_ref")
    _limitations(rules, p.get("limitations"))
    for mapping in _list(rules, p.get("source_mappings")):
        item = _shape(rules, mapping, ("source", "field", "location"), ("start", "end"))
        _ref(rules, item.get("source"))
        _text(rules, item.get("field"))
        start, end = item.get("start"), item.get("end")
        ok = (start is None and end is None) or _span(start, end, None)
        _check(rules, "mapping_range", ok, "bad_range")


def _list(rules: frozenset[str], value: Any) -> list[Any]:
    _check(rules, "enum_and_text", isinstance(value, list), "bad_value")
    return value if isinstance(value, list) else []


def _validate_v1(rules: frozenset[str], p: Any) -> None:
    p = _shape(rules, p, V1_FIELDS)
    _common(rules, p)
    flt = _shape(rules, p.get("filtering"), ("disposition",), ("rule_ref",))
    _member(rules, flt.get("disposition"), DISPOSITIONS)
    if flt.get("rule_ref") is not None:
        _ref(rules, flt["rule_ref"])
    pending = flt.get("disposition") == "pending"
    _check(
        rules,
        "pending_no_rule",
        not (pending and flt.get("rule_ref") is not None),
        "pending_with_rule",
    )


def _all_limitations(p: dict[str, Any]) -> list[str]:
    """Return codes from the record, then its attachments, then parsed content."""
    codes = [x["code"] for x in p["limitations"]]
    codes += [x["code"] for a in p["attachments"] for x in a.get("limitations", [])]
    codes += [x["code"] for c in p["parsed_contents"] for x in c["output"]["limitations"]]  # fmt: skip
    return codes


def _validate_v2(rules: frozenset[str], p: Any) -> None:
    p = _shape(rules, p, V2_FIELDS)
    _common(rules, p)
    sel = _shape(rules, p.get("selection"), ("workset_ref", "selection_ref", "ordinal"))
    _text(rules, sel.get("workset_ref"))
    _text(rules, sel.get("selection_ref"))
    _check(rules, "v2_selection_valid", _is_int(sel.get("ordinal")) and sel["ordinal"] >= 0, "bad_value")  # fmt: skip
    _member(rules, p.get("role"), ROLES_V2)
    size = len(p["body"]) if isinstance(p.get("body"), str) else 0
    for zone in _list(rules, p.get("zones")):
        item = _shape(rules, zone, ("kind", "start", "end"))
        _member(rules, item.get("kind"), ZONES)
        s, e = item.get("start"), item.get("end")
        ok = _span(s, e, size)
        _check(rules, "v2_zone_range", ok, "bad_range")
    for rel in _list(rules, p.get("relations")):
        item = _shape(rules, rel, ("kind", "target", "evidence", "scope"))
        _member(rules, item.get("kind"), RELATIONS)
        _ref(rules, item.get("target"))
        _text(rules, item.get("evidence"))
        _text(rules, item.get("scope"))
    lineage = _shape(rules, p.get("lineage"), LINEAGE)
    for name in LINEAGE:
        ref = _shape(rules, lineage.get(name), ("result_id", "kind", "schema_version"))
        _text(rules, ref.get("result_id"))
        ok = ref.get("kind") == name and ref.get("schema_version") == "1"
        _check(rules, "v2_lineage_kinds", ok, "lineage_kind_mismatch")
    _member(rules, p.get("completeness"), ("COMPLETE", "INCOMPLETE"))
    count = len(_all_limitations(p))
    if "status_counts_all_sources" not in rules:
        count = len(p["limitations"])
    ok = (count > 0) == (p["completeness"] == "INCOMPLETE")
    _check(rules, "v2_status_consistency", ok, "status_limitation_mismatch")


def _codes(rules: frozenset[str], p: dict[str, Any]) -> list[str]:
    codes = _all_limitations(p)
    if "limitations_all_sources" not in rules:
        codes = [x["code"] for x in p["limitations"]]
    if "limitation_order" not in rules:
        codes = sorted(codes)
    if "limitation_no_dedupe" not in rules:
        codes = list(dict.fromkeys(codes))
    return codes


def _view(rules: frozenset[str], p: dict[str, Any], version: str) -> dict[str, Any]:
    v2 = version == "2"
    src = p["source"]
    keep = [k for k in p if "preserve_all_fields" in rules or k not in V2_ONLY]
    verbatim = "text_verbatim" in rules
    text = lambda v: v if verbatim or not isinstance(v, str) else v.strip()
    ident = lambda x: None if x is None else x["identity"]
    view: dict[str, Any] = {
        "kind_version": f"prepared@{version}",
        "source_ref": f"{src['kind']}/{src['identity']}/{src['version']}",
        "source_type": p["source_type"],
        "triage_input_line": f"triage_input@{version}",
        "sender_identity": ident(p["sender"]),
        "author_identity": ident(p["author"]),
        "recipient_roles": [r["role"] for r in p["recipients"]],
        "source_time": p["source_time"],
        "subject": text(p["subject"]),
        "body": text(p["body"]),
        "filtering_disposition": None if v2 else p["filtering"]["disposition"],
        "completeness": p["completeness"] if v2 else None,
        "limitation_codes": _codes(rules, p),
        "attachment_refs": [
            "/".join(a["reference"][k] for k in ("kind", "identity", "version"))
            for a in p["attachments"]
        ],
        "preserved_field_count": len(keep),
        "dropped_fields": sorted(set(p) - set(keep)),
        "invented_fields": [],
    }
    if not v2 and "no_invented_fields" not in rules:
        view["invented_fields"] = ["relations", "zones"]
    if v2:
        view["role"] = p["role"]
        view["selection_ordinal"] = p["selection"]["ordinal"]
        view["zone_kinds"] = [z["kind"] for z in p["zones"]]
        view["relation_kinds"] = [r["kind"] for r in p["relations"]]
    return view


def _route(rules: frozenset[str], stored: dict[str, Any]) -> str:
    kind, version = stored["kind"], stored["schema_version"]
    if "label_kind_exact" in rules and kind != "prepared":
        raise Reject("unknown_version")
    exact = isinstance(version, str) and version in ("1", "2")
    if "label_version_exact" in rules and not exact:
        raise Reject("unknown_version")
    if exact:
        return version
    return "1" if str(version).lstrip("0") == "1" else "2"


def evaluate(case: Case, bases: dict[str, Any], off: frozenset[str] = frozenset()) -> Case:  # fmt: skip
    """Return the decision of the reference reader, with some rules switched off."""
    rules = frozenset(RULES) - off
    inp = case["input"]
    stored = inp["stored"]
    try:
        payload = materialize(stored, bases)
        version = _route(rules, stored)
        if inp["operation"] == "force_v1_codec" and "v1_codec_strict" in rules:
            version = "1"
        (_validate_v2 if version == "2" else _validate_v1)(rules, payload)
        reader = "v2" if version == "2" else "v1_historical"
        if inp["operation"] == "project_to_v1":
            _check(rules, "projection_forbidden", False, "lossy_projection_forbidden")
        if inp["operation"] == "bind_triage_input":
            _check(rules, "binding_line", inp["target"] == f"triage_input@{version}", "ref_version_not_allowed")  # fmt: skip
            return {"decision": "accept", "reader": reader, "binding": inp["target"]}
        return {"decision": "accept", "reader": reader, "view": _view(rules, payload, version)}  # fmt: skip
    except Reject as error:
        return {"decision": "reject", "code": error.code}
    except (KeyError, TypeError, AttributeError, ValueError, IndexError):
        return {"decision": "crash"}
