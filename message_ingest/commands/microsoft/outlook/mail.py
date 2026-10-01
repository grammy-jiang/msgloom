"""Outlook Mail command dispatch."""

from __future__ import annotations

import argparse
from typing import Any

from scrapy.exceptions import UsageError

from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1
from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
    MailRulePolicy,
    parse_mail_rule_policy,
)
from message_ingest.commands._common import run_graph
from message_ingest.commands.microsoft.outlook.sync import run_mail_sync
from message_ingest.commands.microsoft.validation import reject_options
from msgloom.configuration import (
    ConfigurationError,
    format_configuration_error,
    load_universal_config,
)


def _load_mail_rule_policy(opts: argparse.Namespace) -> MailRulePolicy:
    try:
        document = load_universal_config(getattr(opts, "config", None))
        return parse_mail_rule_policy(
            document.outlook_mail_values(),
            source_label=document.source,
        )
    except ConfigurationError as error:
        raise UsageError(format_configuration_error(error)) from None


def dispatch_mail(command: Any, opts: argparse.Namespace) -> None:
    """Map Outlook Mail actions to their existing spiders."""
    if opts.action == "discover":
        if opts.message_ids:
            raise UsageError("Mail discover does not accept MESSAGE_ID values")
        reject_options(opts, allowed={"folder", "page_size", "max_pages"})
        policy = _load_mail_rule_policy(opts)
        run_graph(
            command,
            "outlook_discover",
            {
                "folder": opts.folder or "",
                "page_size": str(opts.page_size or 25),
                "max_pages": str(0 if opts.max_pages is None else opts.max_pages),
                "_mail_rule_policy": policy,
            },
        )
        return
    if opts.action == "delta":
        if opts.message_ids:
            raise UsageError("Mail delta does not accept MESSAGE_ID values")
        reject_options(opts, allowed={"page_size", "reconcile"})
        policy = _load_mail_rule_policy(opts)
        if policy.enabled:
            raise UsageError("enabled Mail rules require 'microsoft outlook mail sync'")
        reconcile = True if opts.reconcile is None else opts.reconcile
        run_graph(
            command,
            "outlook_delta",
            {
                "page_size": str(opts.page_size or 25),
                "reconcile_global": "1" if reconcile else "0",
                "_mail_rule_policy": policy,
            },
        )
        return
    if opts.action == "sync":
        if opts.message_ids:
            raise UsageError("Mail sync does not accept MESSAGE_ID values")
        reject_options(opts, allowed={"page_size", "reconcile", "max_enrich"})
        policy = _load_mail_rule_policy(opts)
        if policy.enabled and opts.max_enrich is not None:
            raise UsageError(
                "--max-enrich is incompatible with enabled Outlook Mail rules"
            )
        run_mail_sync(command, opts, mail_rule_policy=policy)
        return
    if opts.action == "full":
        reject_options(opts, allowed={"operation", "acquisition_profile"})
        message_ids = tuple(
            dict.fromkeys(
                cleaned for value in opts.message_ids if (cleaned := value.strip())
            )
        )
        if not message_ids:
            raise UsageError("at least one MESSAGE_ID is required")
        profile = opts.acquisition_profile or FULL_V1
        if profile != FULL_V1:
            raise UsageError("Mail full requires the Outlook Mail acquisition profile")
        run_graph(
            command,
            "outlook_full",
            {
                "message_ids": ",".join(message_ids),
                "operation": opts.operation or "refresh",
                "profile": profile,
            },
        )
        return
    raise UsageError("use 'microsoft outlook mail {discover,delta,full,sync}'")


__all__ = ["dispatch_mail"]
