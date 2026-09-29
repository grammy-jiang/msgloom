"""Execution-only bounded resolution for approved credential references."""

from __future__ import annotations

import os
import stat
from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from pathlib import Path

from pydantic import SecretStr

from .errors import ConfigurationError, ConfigurationErrorCode
from .models import SecretBinding, SecretSource

MAX_SECRET_BYTES = 16 * 1024


class SecretResolver:
    """Resolve only caller-whitelisted environment variables or mounted files."""

    __slots__ = ("_allowed_environment", "_allowed_files", "_environ", "_root")

    def __init__(
        self,
        *,
        allowed_environment: AbstractSet[str],
        allowed_files: AbstractSet[str],
        mounted_secret_dir: Path | None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._allowed_environment = frozenset(allowed_environment)
        self._allowed_files = frozenset(allowed_files)
        self._root = mounted_secret_dir
        self._environ = os.environ if environ is None else environ

    def resolve(self, binding: SecretBinding) -> SecretStr:
        """Resolve one configured binding only when execution explicitly asks."""
        if binding.source is SecretSource.ENVIRONMENT:
            return self._environment(binding.locator)
        return self._mounted_file(binding.locator)

    def _environment(self, locator: str) -> SecretStr:
        if locator not in self._allowed_environment:
            raise ConfigurationError(ConfigurationErrorCode.SECRET_NOT_APPROVED)
        value = self._environ.get(locator)
        if value is None or not value or len(value.encode("utf-8")) > MAX_SECRET_BYTES:
            raise ConfigurationError(ConfigurationErrorCode.SECRET_UNAVAILABLE)
        return SecretStr(value)

    def _mounted_file(self, locator: str) -> SecretStr:
        if locator not in self._allowed_files or self._root is None:
            raise ConfigurationError(ConfigurationErrorCode.SECRET_NOT_APPROVED)
        if Path(locator).name != locator:
            raise ConfigurationError(ConfigurationErrorCode.SECRET_NOT_APPROVED)
        try:
            root_fd = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                fd = os.open(
                    locator,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=root_fd,
                )
            finally:
                os.close(root_fd)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SECRET_BYTES:
                    raise ConfigurationError(ConfigurationErrorCode.SECRET_UNAVAILABLE)
                data = os.read(fd, MAX_SECRET_BYTES + 1)
            finally:
                os.close(fd)
        except ConfigurationError:
            raise
        except OSError:
            raise ConfigurationError(
                ConfigurationErrorCode.SECRET_UNAVAILABLE
            ) from None
        if not data or len(data) > MAX_SECRET_BYTES:
            raise ConfigurationError(ConfigurationErrorCode.SECRET_UNAVAILABLE)
        try:
            value = data.decode("utf-8").rstrip("\r\n")
        except UnicodeDecodeError:
            raise ConfigurationError(
                ConfigurationErrorCode.SECRET_UNAVAILABLE
            ) from None
        if not value:
            raise ConfigurationError(ConfigurationErrorCode.SECRET_UNAVAILABLE)
        return SecretStr(value)
