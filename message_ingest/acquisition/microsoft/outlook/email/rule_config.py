"""Closed user configuration for deterministic Outlook Mail acquisition rules."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, ClassVar, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from msgloom.configuration import (
    ConfigurationDiagnostic,
    ConfigurationError,
    ConfigurationErrorCode,
)
from msgloom.configuration.validation import canonical_json

from .profile import DISCOVERY_V1, FULL_V1
from .rule_regex import (
    MAX_REGEX_PATTERNS,
    MSGLOOM_REGEX_VERSION,
    MailRegexEngine,
    MailRegexSyntaxError,
)

MAIL_RULE_POLICY_FAMILY = "outlook-mail-acquisition-rules-v1"
MAIL_PROFILE_LATTICE_VERSION = "outlook-mail-profile-lattice-v1"

_MAX_RULES = 256
_MAX_EXCEPTIONS = 32
_MAX_VALUES = 128
_MAX_SIZE_KB = 2_097_151
_RULE_ID = re.compile(r"[A-Za-z0-9_.:-]{1,96}\Z")
_SAFE_SOURCES = frozenset({"builtin", "default", "explicit"})
# fmt: off
_REGEX_PREDICATES = frozenset(
    ["subject_regex", "body_regex", "body_or_subject_regex", "from_address_regex", "sender_address_regex", "to_address_regex", "cc_address_regex", "bcc_address_regex", "recipient_address_regex", "reply_to_address_regex", "header_regex", "item_class_regex"]
)
_ADDRESS_LITERAL_PREDICATES = frozenset(
    ["from_addresses", "from_address_contains", "sender_addresses", "sender_address_contains", "to_addresses", "to_address_contains", "cc_addresses", "cc_address_contains", "bcc_addresses", "bcc_address_contains", "recipient_address_contains", "reply_to_addresses", "reply_to_address_contains"]
)
_DATETIME_PREDICATES = frozenset(
    "received_after received_before sent_after sent_before created_after created_before".split()  # noqa: SIM905
)
_STRING_LIST_PREDICATES = frozenset(
    ["subject_contains", "subject_exact", "subject_regex", "body_contains", "body_regex", "body_or_subject_contains", "body_or_subject_regex", "from_addresses", "from_contains", "from_address_contains", "from_address_regex", "sender_addresses", "sender_contains", "sender_address_contains", "sender_address_regex", "to_addresses", "to_address_contains", "to_address_regex", "cc_addresses", "cc_address_contains", "cc_address_regex", "bcc_addresses", "bcc_address_contains", "bcc_address_regex", "recipient_contains", "recipient_address_contains", "recipient_address_regex", "reply_to_addresses", "reply_to_address_contains", "reply_to_address_regex", "categories", "header_contains", "header_regex", "item_class_exact", "item_class_contains", "item_class_regex"]
)
_ENUM_LIST_PREDICATES = frozenset(
    {"importance", "sensitivity", "inference_classification", "followup_status"}
)
# fmt: on

StringValues = tuple[str, ...]


class _CasefoldEnum(StrEnum):
    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            folded = value.casefold()
            for member in cls:
                if member.value.casefold() == folded:
                    return member
        return None


class MailRuleProfile(_CasefoldEnum):
    DISCOVERY = "discovery"
    FULL = "full"


class MailImportance(_CasefoldEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class MailSensitivity(_CasefoldEnum):
    NORMAL = "normal"
    PERSONAL = "personal"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


class MailInferenceClassification(_CasefoldEnum):
    FOCUSED = "focused"
    OTHER = "other"


class MailFollowupStatus(_CasefoldEnum):
    NOT_FLAGGED = "not_flagged"
    FLAGGED = "flagged"
    COMPLETE = "complete"


class _ClosedFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _bounded_string_list(value: object) -> object:
    if not isinstance(value, (list, tuple)):
        return value
    if not value or len(value) > _MAX_VALUES:
        raise PydanticCustomError("bound_exceeded", "bounded list required")
    return value


class MailRulePredicates(_ClosedFrozenModel):
    """One flat V1 predicate block: fields AND, values within a field OR."""

    subject_contains: StringValues | None = None
    subject_exact: StringValues | None = None
    subject_regex: StringValues | None = None
    body_contains: StringValues | None = None
    body_regex: StringValues | None = None
    body_or_subject_contains: StringValues | None = None
    body_or_subject_regex: StringValues | None = None
    from_addresses: StringValues | None = None
    from_contains: StringValues | None = None
    from_address_contains: StringValues | None = None
    from_address_regex: StringValues | None = None
    sender_addresses: StringValues | None = None
    sender_contains: StringValues | None = None
    sender_address_contains: StringValues | None = None
    sender_address_regex: StringValues | None = None
    to_addresses: StringValues | None = None
    to_address_contains: StringValues | None = None
    to_address_regex: StringValues | None = None
    cc_addresses: StringValues | None = None
    cc_address_contains: StringValues | None = None
    cc_address_regex: StringValues | None = None
    bcc_addresses: StringValues | None = None
    bcc_address_contains: StringValues | None = None
    bcc_address_regex: StringValues | None = None
    recipient_contains: StringValues | None = None
    recipient_address_contains: StringValues | None = None
    recipient_address_regex: StringValues | None = None
    reply_to_addresses: StringValues | None = None
    reply_to_address_contains: StringValues | None = None
    reply_to_address_regex: StringValues | None = None
    categories: StringValues | None = None
    importance: tuple[MailImportance, ...] | None = None
    has_attachments: bool | None = None
    header_contains: StringValues | None = None
    header_regex: StringValues | None = None
    sensitivity: tuple[MailSensitivity, ...] | None = None
    message_size_min_kb: Annotated[int, Field(ge=0, le=_MAX_SIZE_KB)] | None = None
    message_size_max_kb: Annotated[int, Field(ge=0, le=_MAX_SIZE_KB)] | None = None
    received_after: datetime | None = None
    received_before: datetime | None = None
    sent_after: datetime | None = None
    sent_before: datetime | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    is_read: bool | None = None
    is_draft: bool | None = None
    inference_classification: tuple[MailInferenceClassification, ...] | None = None
    followup_status: tuple[MailFollowupStatus, ...] | None = None
    item_class_exact: StringValues | None = None
    item_class_contains: StringValues | None = None
    item_class_regex: StringValues | None = None
    is_meeting_request: bool | None = None
    is_meeting_response: bool | None = None
    is_non_delivery_report: bool | None = None
    is_read_receipt: bool | None = None

    _REGEX_FIELDS: ClassVar[frozenset[str]] = _REGEX_PREDICATES
    _ADDRESS_LITERAL_FIELDS: ClassVar[frozenset[str]] = _ADDRESS_LITERAL_PREDICATES
    _DATETIME_FIELDS: ClassVar[frozenset[str]] = _DATETIME_PREDICATES
    _STRING_LIST_FIELDS: ClassVar[frozenset[str]] = _STRING_LIST_PREDICATES
    _ENUM_LIST_FIELDS: ClassVar[frozenset[str]] = _ENUM_LIST_PREDICATES

    @field_validator("*", mode="before")
    @classmethod
    def _validate_field_input(cls, value: object, info: Any) -> object:
        name = info.field_name
        if name in cls._STRING_LIST_FIELDS or name in cls._ENUM_LIST_FIELDS:
            value = _bounded_string_list(value)
        if name in cls._STRING_LIST_FIELDS and isinstance(value, (list, tuple)):
            result: list[str] = []
            for item in value:
                if not isinstance(item, str):
                    raise PydanticCustomError("invalid_value", "string value required")
                if name in cls._ADDRESS_LITERAL_FIELDS:
                    item = item.strip()
                if not item:
                    raise PydanticCustomError("invalid_value", "empty value forbidden")
                result.append(item)
            return result
        return value

    @field_validator("*")
    @classmethod
    def _validate_field_value(cls, value: object, info: Any) -> object:
        if value is None:
            return value
        name = info.field_name
        if name in cls._REGEX_FIELDS:
            assert isinstance(value, tuple)
            seen: set[str] = set()
            for pattern in value:
                if pattern in seen:
                    raise PydanticCustomError("duplicate_value", "duplicate regex")
                seen.add(pattern)
                try:
                    MailRegexEngine.compile(pattern)
                except MailRegexSyntaxError:
                    raise PydanticCustomError(
                        "invalid_regex", "invalid regex"
                    ) from None
            return value
        if name in cls._STRING_LIST_FIELDS:
            assert isinstance(value, tuple)
            seen_folded: set[str] = set()
            for item in value:
                folded = item.casefold()
                if folded in seen_folded:
                    raise PydanticCustomError("duplicate_value", "duplicate value")
                seen_folded.add(folded)
            return value
        if name in cls._ENUM_LIST_FIELDS:
            assert isinstance(value, tuple)
            keys = [cast(StrEnum, item).value for item in value]
            if len(keys) != len(set(keys)):
                raise PydanticCustomError("duplicate_value", "duplicate enum")
            return value
        if name in cls._DATETIME_FIELDS:
            assert isinstance(value, datetime)
            if value.tzinfo is None or value.utcoffset() is None:
                raise PydanticCustomError("invalid_range", "timezone required")
        return value

    @model_validator(mode="after")
    def _validate_block(self) -> MailRulePredicates:
        if not self.model_fields_set:
            raise PydanticCustomError("empty_block", "predicate block is empty")
        if (
            self.message_size_min_kb is not None
            and self.message_size_max_kb is not None
            and self.message_size_min_kb > self.message_size_max_kb
        ):
            raise PydanticCustomError("invalid_range", "inverted size range")
        return self


class MailRuleDefinition(_ClosedFrozenModel):
    id: str
    sequence: Annotated[int, Field(ge=0, le=2_147_483_647)]
    enabled: bool = True
    profile: MailRuleProfile
    stop_processing: bool = False
    conditions: MailRulePredicates
    exceptions: tuple[MailRulePredicates, ...] = ()

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        if _RULE_ID.fullmatch(value) is None:
            raise PydanticCustomError("invalid_value", "invalid rule identifier")
        return value

    @field_validator("exceptions", mode="before")
    @classmethod
    def _validate_exceptions(cls, value: object) -> object:
        if not isinstance(value, (list, tuple)):
            return value
        if len(value) > _MAX_EXCEPTIONS:
            raise PydanticCustomError("bound_exceeded", "too many exceptions")
        return value


class MailRulePolicy(_ClosedFrozenModel):
    enabled: bool = False
    default_profile: MailRuleProfile = MailRuleProfile.DISCOVERY
    rules: tuple[MailRuleDefinition, ...] = ()

    @field_validator("rules", mode="before")
    @classmethod
    def _validate_rules_bound(cls, value: object) -> object:
        if not isinstance(value, (list, tuple)):
            return value
        if len(value) > _MAX_RULES:
            raise PydanticCustomError("bound_exceeded", "too many rules")
        return value

    @model_validator(mode="after")
    def _validate_policy(self) -> MailRulePolicy:
        ids = [rule.id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise PydanticCustomError("duplicate_rule_id", "duplicate rule id")
        sequences = [rule.sequence for rule in self.rules]
        if len(sequences) != len(set(sequences)):
            raise PydanticCustomError("duplicate_sequence", "duplicate sequence")
        regex_count = sum(_rule_regex_count(rule) for rule in self.rules)
        if regex_count > MAX_REGEX_PATTERNS:
            raise PydanticCustomError("bound_exceeded", "too many regex patterns")
        return self


def parse_mail_rule_policy(
    raw: Mapping[str, object] | None,
    *,
    source_label: str | None = None,
) -> MailRulePolicy:
    """Validate one Mail policy while exposing only bounded diagnostic metadata."""

    if source_label is not None and source_label not in _SAFE_SOURCES:
        raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT)
    try:
        return MailRulePolicy.model_validate(dict(raw or {}))
    except ValidationError as error:
        detail = error.errors(include_input=False, include_url=False)[0]
        loc = cast(tuple[object, ...], detail.get("loc", ()))
        reason = _reason_code(detail, loc)
        raise ConfigurationError(
            ConfigurationErrorCode.UNKNOWN_INPUT
            if reason == "unknown_field"
            else ConfigurationErrorCode.INVALID_INPUT,
            ConfigurationDiagnostic(
                source_label=source_label,
                field_path=_safe_field_path(loc),
                reason_code=reason,
            ),
        ) from None


def internal_mail_profile(profile: MailRuleProfile) -> str:
    """Map simple user vocabulary to versioned acquisition contracts."""

    if profile is MailRuleProfile.DISCOVERY:
        return DISCOVERY_V1
    return FULL_V1


def effective_mail_policy_digest(policy: MailRulePolicy) -> str:
    """Hash canonical effective policy material for private control state."""

    material = _effective_policy_material(policy)
    encoded = canonical_json(material).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def mail_policy_inspection(policy: MailRulePolicy) -> dict[str, object]:
    """Return only safe non-content policy metadata."""

    return {
        "enabled": policy.enabled,
        "policy_family": MAIL_RULE_POLICY_FAMILY,
        "rule_count": len(policy.rules),
        "enabled_rule_count": sum(rule.enabled for rule in policy.rules),
    }


def _reason_code(detail: Mapping[str, Any], loc: tuple[object, ...]) -> str:
    error_type = str(detail.get("type", "invalid_value"))
    if error_type == "extra_forbidden":
        return "unknown_field"
    if error_type in {
        "bound_exceeded",
        "greater_than_equal",
        "less_than_equal",
        "too_long",
    }:
        return "bound_exceeded"
    if error_type in {
        "duplicate_rule_id",
        "duplicate_sequence",
        "invalid_regex",
        "invalid_range",
    }:
        return error_type
    if error_type == "enum" and loc and loc[-1] in {"profile", "default_profile"}:
        return "unsupported_profile"
    if error_type.startswith("datetime") or error_type in {
        "timezone_aware",
        "date_type",
    }:
        return "invalid_range"
    return "invalid_range"


def _safe_field_path(loc: tuple[object, ...]) -> str:
    known = (
        set(MailRulePolicy.model_fields)
        | set(MailRuleDefinition.model_fields)
        | set(MailRulePredicates.model_fields)
    )
    result = "acquisition.microsoft.outlook.mail"
    for segment in loc:
        if isinstance(segment, int):
            result += f"[{segment}]"
        elif isinstance(segment, str):
            safe = segment if segment in known else "<unknown>"
            result += f".{safe}"
    return result


def _rule_regex_count(rule: MailRuleDefinition) -> int:
    return _predicate_regex_count(rule.conditions) + sum(
        _predicate_regex_count(block) for block in rule.exceptions
    )


def _predicate_regex_count(predicates: MailRulePredicates) -> int:
    return sum(
        len(cast(tuple[str, ...], getattr(predicates, field)) or ())
        for field in MailRulePredicates._REGEX_FIELDS
    )


def _effective_policy_material(policy: MailRulePolicy) -> object:
    if not policy.enabled:
        return {
            "contract": MAIL_RULE_POLICY_FAMILY,
            "enabled": False,
        }
    rules = [
        _canonical_rule(rule)
        for rule in sorted(
            (rule for rule in policy.rules if rule.enabled),
            key=lambda rule: rule.sequence,
        )
    ]
    return {
        "contract": MAIL_RULE_POLICY_FAMILY,
        "enabled": True,
        "regex_contract": MSGLOOM_REGEX_VERSION,
        "profile_lattice": MAIL_PROFILE_LATTICE_VERSION,
        "default_profile": policy.default_profile.value,
        "rules": rules,
    }


def _canonical_rule(rule: MailRuleDefinition) -> dict[str, object]:
    exceptions = [_canonical_predicates(block) for block in rule.exceptions]
    exceptions.sort(key=_canonical_sort_key)
    return {
        "id": rule.id,
        "sequence": rule.sequence,
        "profile": rule.profile.value,
        "stop_processing": rule.stop_processing,
        "conditions": _canonical_predicates(rule.conditions),
        "exceptions": exceptions,
    }


def _canonical_predicates(predicates: MailRulePredicates) -> dict[str, object]:
    result: dict[str, object] = {}
    for field in sorted(MailRulePredicates.model_fields):
        value = getattr(predicates, field)
        if value is None:
            continue
        if isinstance(value, tuple):
            if field in MailRulePredicates._REGEX_FIELDS:
                result[field] = sorted(cast(tuple[str, ...], value))
            elif value and isinstance(value[0], StrEnum):
                result[field] = sorted(cast(StrEnum, item).value for item in value)
            else:
                result[field] = sorted(
                    cast(str, item).casefold() for item in cast(tuple[str, ...], value)
                )
        elif isinstance(value, datetime):
            result[field] = value.astimezone(UTC).isoformat()
        elif isinstance(value, StrEnum):
            result[field] = value.value
        else:
            result[field] = value
    return result


def _canonical_sort_key(value: object) -> str:
    return canonical_json(value)
