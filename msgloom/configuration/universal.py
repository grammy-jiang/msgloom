"""One hardened universal msgloom user-configuration document."""

from __future__ import annotations

import copy
import os
import stat
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal, cast

from .errors import (
    ConfigurationDiagnostic,
    ConfigurationError,
    ConfigurationErrorCode,
)
from .models import OperatorSettings

MAX_CONFIG_BYTES = 256 * 1024

UniversalConfigSource = Literal["builtin", "default", "explicit"]

_OPERATOR_TOP_LEVEL = frozenset(OperatorSettings.model_fields)
_UNIVERSAL_TOP_LEVEL = _OPERATOR_TOP_LEVEL | {"acquisition"}


@dataclass(frozen=True, slots=True)
class UniversalConfigDocument:
    """Frozen file snapshot with detached operation-specific projections."""

    source: UniversalConfigSource
    path: Path | None
    values: Mapping[str, object]

    def operator_values(self) -> dict[str, object] | None:
        """Return only legacy operator roots, detached from the document snapshot."""

        result = {
            key: copy.deepcopy(value)
            for key, value in self.values.items()
            if key in _OPERATOR_TOP_LEVEL
        }
        return result or None

    def outlook_mail_values(self) -> dict[str, object] | None:
        """Return the Outlook Mail acquisition subtree when present."""

        acquisition = self.values.get("acquisition")
        if acquisition is None:
            return None
        if not isinstance(acquisition, Mapping):
            raise _shape_error(self.source, "acquisition")
        microsoft = acquisition.get("microsoft")
        if microsoft is None:
            return None
        if not isinstance(microsoft, Mapping):
            raise _shape_error(self.source, "acquisition.microsoft")
        outlook = microsoft.get("outlook")
        if outlook is None:
            return None
        if not isinstance(outlook, Mapping):
            raise _shape_error(self.source, "acquisition.microsoft.outlook")
        mail = outlook.get("mail")
        if mail is None:
            return None
        if not isinstance(mail, Mapping):
            raise _shape_error(self.source, "acquisition.microsoft.outlook.mail")
        return copy.deepcopy(dict(mail))


def load_universal_config(config_file: Path | None = None) -> UniversalConfigDocument:
    """Load one explicit or XDG-default universal config snapshot."""

    if config_file is None:
        source: UniversalConfigSource = "default"
        path = _default_config_path()
    else:
        source = "explicit"
        path = config_file.expanduser().absolute()

    try:
        data = _read_bounded(path, MAX_CONFIG_BYTES)
    except FileNotFoundError:
        if config_file is None:
            return UniversalConfigDocument(
                source="builtin",
                path=None,
                values=MappingProxyType({}),
            )
        raise ConfigurationError(
            ConfigurationErrorCode.INVALID_INPUT,
            ConfigurationDiagnostic(
                source_label=source,
                reason_code="config_missing",
            ),
        ) from None
    except ConfigurationError as error:
        reason = (
            "bound_exceeded"
            if error.code is ConfigurationErrorCode.INPUT_TOO_LARGE
            else "invalid_file"
        )
        raise ConfigurationError(
            error.code,
            ConfigurationDiagnostic(
                source_label=source,
                reason_code=reason,
            ),
        ) from None
    except OSError:
        raise ConfigurationError(
            ConfigurationErrorCode.INVALID_INPUT,
            ConfigurationDiagnostic(
                source_label=source,
                reason_code="invalid_file",
            ),
        ) from None

    values = _decode_universal_toml(data, source)
    unknown = set(values) - _UNIVERSAL_TOP_LEVEL
    if unknown:
        raise ConfigurationError(
            ConfigurationErrorCode.UNKNOWN_INPUT,
            ConfigurationDiagnostic(
                source_label=source,
                field_path="<unknown>",
                reason_code="unknown_field",
            ),
        )
    snapshot = copy.deepcopy(values)
    return UniversalConfigDocument(
        source=source,
        path=path,
        values=MappingProxyType(snapshot),
    )


def load_operator_configuration_from_document(
    document: UniversalConfigDocument,
    *,
    command_options: Mapping[str, object] | None = None,
    mounted_secret_dir: Path | None = None,
):
    """Lazy compatibility wrapper to avoid a universal/legacy loader import cycle."""

    from .loader import load_operator_configuration_from_document as load

    return load(
        document,
        command_options=command_options,
        mounted_secret_dir=mounted_secret_dir,
    )


def _default_config_path() -> Path:
    configured = os.environ.get("XDG_CONFIG_HOME")
    if configured:
        candidate = Path(configured)
        if candidate.is_absolute():
            return candidate / "msgloom" / "msgloom.toml"
    return Path.home() / ".config" / "msgloom" / "msgloom.toml"


def _decode_universal_toml(
    data: bytes,
    source: UniversalConfigSource,
) -> dict[str, object]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ConfigurationError(
            ConfigurationErrorCode.INVALID_INPUT,
            ConfigurationDiagnostic(
                source_label=source,
                reason_code="invalid_utf8",
            ),
        ) from None
    try:
        value = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        line = column = None
        marker = "(at line "
        _prefix, separator, tail = str(error).rpartition(marker)
        if separator:
            line_text, column_separator, remainder = tail.partition(", column ")
            column_text, closing, _suffix = remainder.partition(")")
            if (
                column_separator
                and closing
                and line_text.isdigit()
                and column_text.isdigit()
            ):
                line = int(line_text)
                column = int(column_text)
        raise ConfigurationError(
            ConfigurationErrorCode.INVALID_INPUT,
            ConfigurationDiagnostic(
                source_label=source,
                line=line,
                column=column,
                reason_code="invalid_toml",
            ),
        ) from None
    if not isinstance(value, dict):
        raise ConfigurationError(
            ConfigurationErrorCode.INVALID_INPUT,
            ConfigurationDiagnostic(
                source_label=source,
                reason_code="invalid_toml",
            ),
        )
    return cast(dict[str, object], value)


def _shape_error(source: UniversalConfigSource, field_path: str) -> ConfigurationError:
    return ConfigurationError(
        ConfigurationErrorCode.INVALID_INPUT,
        ConfigurationDiagnostic(
            source_label=source,
            field_path=field_path,
            reason_code="invalid_file",
        ),
    )


def _read_bounded(path: Path, maximum: int) -> bytes:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        raise
    except OSError:
        raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT) from None
    try:
        return _read_regular_fd(fd, maximum)
    finally:
        os.close(fd)


def _read_regular_fd(fd: int, maximum: int) -> bytes:
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT)
        if info.st_size > maximum:
            raise ConfigurationError(ConfigurationErrorCode.INPUT_TOO_LARGE)
        data = os.read(fd, maximum + 1)
    except ConfigurationError:
        raise
    except OSError:
        raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT) from None
    if len(data) > maximum:
        raise ConfigurationError(ConfigurationErrorCode.INPUT_TOO_LARGE)
    return data


def _decode_utf8(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT) from None


__all__ = [
    "MAX_CONFIG_BYTES",
    "UniversalConfigDocument",
    "UniversalConfigSource",
    "load_operator_configuration_from_document",
    "load_universal_config",
]
