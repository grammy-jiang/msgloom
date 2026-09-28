"""Acquire Outlook folder changes and commit complete delta rounds."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote, urlencode

import scrapy
from scrapy.http import TextResponse
from twisted.python.failure import Failure

from message_ingest.items.acquisition import AcquisitionFailureItem
from message_ingest.items.microsoft.outlook.email import (
    OutlookDeltaCheckpointCandidateItem,
    OutlookMailRemovalItem,
)
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)
from microsoft_graph.protocol import GraphDeltaPage

from ._delta_state import MailDeltaExecutionState, execution_payload
from ._folders import OutlookFolderTraversal


class OutlookDeltaSpider(OutlookFolderTraversal):
    """
    Synchronize each inventoried folder and reconcile otherwise unseen
    messages.

    Graph delta links are provider checkpoints.
    :class:`~scrapy.extensions.spiderstate.SpiderState` holds execution facts
    for a clean ``JOBDIR`` resume. Keep those two state lifetimes separate:
    only the idle extension can promote candidate links after all required work
    succeeds.
    """

    name = "outlook_delta"

    def __init__(
        self,
        *args,
        page_size: str = "25",
        reconcile_global: str = "1",
        **kwargs,
    ) -> None:
        """
        Create execution state that Scrapy
        :class:`~scrapy.extensions.spiderstate.SpiderState` can replace on
        resume.
        """
        super().__init__(*args, **kwargs)
        self.state: dict[str, Any] = {}
        self.page_size = self._bounded_int(
            page_size, name="page_size", minimum=1, maximum=1000
        )
        self.reconcile_global = reconcile_global.strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
        self._completed_folder_ids: set[str] = set()
        self._delta_links: dict[str, str] = {}
        self._delta_start_scheduled = False

    async def start(self):
        """
        Load committed cursors and schedule folder inventory only for a new
        run.

        On ``JOBDIR`` resume, queued callbacks and the saved run ID continue
        the same round; restarting inventory would double-count work and could
        mix checkpoint candidates.
        """
        self._restore_execution_state()
        self.logger.info(
            "Starting Outlook delta crawl: page_size=%s reconciliation=%s",
            self.page_size,
            self.reconcile_global,
        )
        store = OutlookDeltaCheckpointStore.from_crawler(self.crawler)
        self._delta_links = await asyncio.to_thread(store.get_delta_links)
        self.crawler.stats.set_value(
            "msgloom/crawl/delta/checkpoint_loaded_count", len(self._delta_links)
        )
        self.crawler.stats.set_value("msgloom/crawl/mode", "delta")
        self.crawler.stats.set_value("msgloom/crawl/run_id", self.run_id)
        self.crawler.stats.set_value(
            "msgloom/crawl/delta/folder_started_count",
            len(self._started_folder_ids),
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/delta/folder_completed_count",
            len(self._completed_folder_ids),
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/delta/folder_inventory_completed",
            self._folder_inventory_complete,
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/delta/folder_inventory_failed",
            self._folder_inventory_failed,
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/reconcile/enabled", self.reconcile_global
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/reconcile/completed", self._reconcile_complete
        )
        if self._delta_start_scheduled:
            self.crawler.stats.set_value("msgloom/crawl/delta/job_resumed", True)
            return
        self._delta_start_scheduled = True
        self._persist_execution_state()
        yield self._folder_list_request(
            self._mailbox_url("/mailFolders?")
            + urlencode({"includeHiddenFolders": "true", "$top": self.page_size}),
            parent_folder_id=None,
            page_number=1,
            purpose="folder-list",
        )

    def parse_message_delta(
        self,
        response: TextResponse,
        *,
        purpose: str,
        folder_id: str,
        page_number: int,
        from_checkpoint: bool,
        reset_count: int,
    ):
        """
        Emit changes and stage a candidate only at the end of a folder round.

        An ``@odata.nextLink`` always takes precedence. A page with neither
        continuation nor delta state is a failed round, even when its HTTP
        status and message payload are valid. Folder removals describe
        membership changes, not confirmed mailbox deletion.
        """
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        # Compatibility: missing value is empty and nextLink wins. Link
        # validation stays after observations, before scheduling/promotion.
        page = GraphDeltaPage.from_payload(
            response.json(),
            strict=False,
            missing_value_empty=True,
            empty_links_absent=True,
            validate_links=False,
        )
        values = page.values
        self.logger.debug(
            "Processed Outlook delta page: folder=%s page=%s changes=%s from_checkpoint=%s",
            folder_id,
            page_number,
            len(values),
            from_checkpoint,
        )
        self.crawler.stats.inc_value("msgloom/crawl/delta/message_page_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/delta/message_observation_count", count=len(values)
        )

        for message in values:
            if isinstance(removed := message.get("@removed"), dict):
                self.crawler.stats.inc_value(
                    "msgloom/crawl/delta/message_removed_count"
                )
                reason = removed.get("reason")
                if reason:
                    self.crawler.stats.inc_value(
                        f"msgloom/crawl/delta/message_removed_reason_count/{reason}"
                    )
                yield OutlookMailRemovalItem(
                    message_id=message["id"],
                    folder_id=folder_id,
                    removed_reason=reason,
                    raw=message,
                    source_response_url=response.url,
                    observed_at=evidence.observed_at,
                    evidence_id=evidence.evidence_id,
                    run_id=self.run_id,
                )
                continue
            self.crawler.stats.inc_value("msgloom/crawl/delta/message_upsert_count")
            yield self._message_item(
                message,
                response.url,
                evidence.observed_at,
                observation_kind="delta",
                evidence_id=evidence.evidence_id,
            )

        if next_link := page.next_link:
            self.crawler.stats.inc_value(
                "msgloom/crawl/delta/message_continuation_count"
            )
            yield self._message_delta_request(
                next_link,
                folder_id=folder_id,
                page_number=page_number + 1,
                from_checkpoint=from_checkpoint,
                reset_count=reset_count,
            )
            return

        if delta_link := page.delta_link:
            self._completed_folder_ids.add(folder_id)
            self._persist_execution_state()
            self.crawler.stats.set_value(
                "msgloom/crawl/delta/folder_completed_count",
                len(self._completed_folder_ids),
            )
            self.logger.debug(
                "Outlook folder delta round complete: folder=%s completed=%s/%s",
                folder_id,
                len(self._completed_folder_ids),
                len(self._started_folder_ids),
            )
            yield OutlookDeltaCheckpointCandidateItem(
                run_id=self.run_id,
                folder_id=folder_id,
                delta_link=delta_link,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
            )
            return

        self.mark_run_failed("delta_state_missing")
        self.crawler.stats.inc_value("msgloom/crawl/failure_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/failure_purpose_count/message-delta"
        )
        self.crawler.stats.inc_value(
            "msgloom/crawl/failure_type_count/DeltaStateMissing"
        )
        yield AcquisitionFailureItem(
            url=response.url,
            purpose="message-delta",
            error_type="DeltaStateMissing",
            error_message=(
                "Microsoft Graph delta response contained neither "
                "@odata.nextLink nor @odata.deltaLink"
            ),
            observed_at=evidence.observed_at,
            context={"folder_id": folder_id},
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )

    def errback(self, failure: Failure):
        """
        Restart an expired folder cursor once; record other exhausted failures.

        The 410 response remains evidence. Resetting its cursor is recoverable
        until the second attempt fails. Failed folder inventory must block
        reconciliation/commit.
        """
        callback_data = self._failure_request(failure).cb_kwargs
        purpose = callback_data.get("purpose", "unknown")
        evidence = self._failure_evidence_item(failure)
        yield evidence

        if purpose == "message-delta" and evidence.response_status == 410:
            folder_id = callback_data.get("folder_id")
            reset_count = int(callback_data.get("reset_count", 0))
            if folder_id and reset_count < 1:
                self._delta_links.pop(folder_id, None)
                self._completed_folder_ids.discard(folder_id)
                self._persist_execution_state()
                self.crawler.stats.inc_value(
                    "msgloom/crawl/delta/checkpoint_reset_count"
                )
                self.logger.warning(
                    "Outlook delta checkpoint expired; restarting folder delta once: folder=%s",
                    folder_id,
                )
                yield self._initial_message_delta_request(
                    folder_id, reset_count=reset_count + 1
                )
                return

        if purpose in {"folder-list", "folder-child-list"}:
            self._folder_inventory_failed = True
            self._folder_inventory_pending = max(0, self._folder_inventory_pending - 1)
            self.crawler.stats.set_value(
                "msgloom/crawl/delta/folder_inventory_failed", True
            )
        yield self._request_failure_item(failure, evidence)

    def mark_run_failed(self, reason: str) -> None:
        """
        Mirror failure state immediately so a graceful ``JOBDIR`` resume
        retains it.
        """
        super().mark_run_failed(reason)
        self._persist_execution_state()

    def delta_execution_snapshot(self) -> dict[str, Any]:
        """Return the execution facts used to validate checkpoint commits."""
        return {
            "run_id": self.run_id,
            "started_folder_ids": set(self._started_folder_ids),
            "completed_folder_ids": set(self._completed_folder_ids),
            "folder_inventory_complete": self._folder_inventory_complete,
            "folder_inventory_failed": self._folder_inventory_failed,
            "reconcile_complete": self._reconcile_complete,
            "run_failed": self._run_failed,
            "failure_reasons": set(self._failure_reasons),
        }

    def _restore_execution_state(self) -> None:
        """
        Restore the prior run identity and completion sets before queued
        callbacks run.
        """
        saved = self.state.get("msgloom_delta")
        if not isinstance(saved, dict):
            self._persist_execution_state()
            return
        restored = MailDeltaExecutionState.restore(
            saved,
            default_run_id=self.run_id,
        )
        self.run_id = restored.run_id
        self._seen_folder_ids = set(restored.seen_folder_ids)
        self._started_folder_ids = set(restored.started_folder_ids)
        self._completed_folder_ids = set(restored.completed_folder_ids)
        self._reconcile_orphan_ids = set(restored.reconcile_orphan_ids)
        self._folder_inventory_pending = restored.folder_inventory_pending
        self._folder_inventory_complete = restored.folder_inventory_complete
        self._folder_inventory_failed = restored.folder_inventory_failed
        self._reconcile_complete = restored.reconcile_complete
        self._run_failed = restored.run_failed
        self._failure_reasons = set(restored.failure_reasons)
        self._delta_start_scheduled = restored.delta_start_scheduled

    def _persist_execution_state(self) -> None:
        """
        Store plain execution facts in Scrapy's
        :class:`~scrapy.extensions.spiderstate.SpiderState` dictionary.

        Sorting sets keeps snapshots deterministic. This prepares clean
        shutdown/resume; it is not a replacement for transactional provider
        checkpoints.
        """
        self.state["msgloom_delta"] = execution_payload(
            run_id=self.run_id,
            seen_folder_ids=self._seen_folder_ids,
            started_folder_ids=self._started_folder_ids,
            completed_folder_ids=self._completed_folder_ids,
            reconcile_orphan_ids=self._reconcile_orphan_ids,
            folder_inventory_pending=self._folder_inventory_pending,
            folder_inventory_complete=self._folder_inventory_complete,
            folder_inventory_failed=self._folder_inventory_failed,
            reconcile_complete=self._reconcile_complete,
            run_failed=self._run_failed,
            failure_reasons=self._failure_reasons,
            delta_start_scheduled=self._delta_start_scheduled,
        )

    def _message_delta_start_request(self, folder_id: str) -> scrapy.Request:
        """
        Prefer a committed folder cursor; otherwise request the initial delta
        round.
        """
        self.crawler.stats.inc_value("msgloom/crawl/delta/folder_started_count")
        if delta_link := self._delta_links.get(folder_id):
            self.crawler.stats.inc_value("msgloom/crawl/delta/folder_resumed_count")
            return self._message_delta_request(
                delta_link,
                folder_id=folder_id,
                page_number=1,
                from_checkpoint=True,
                reset_count=0,
            )

        self.crawler.stats.inc_value("msgloom/crawl/delta/folder_initial_count")
        return self._initial_message_delta_request(folder_id, reset_count=0)

    def _initial_message_delta_request(
        self, folder_id: str, *, reset_count: int
    ) -> scrapy.Request:
        """
        Build the initial cursor request with a bounded expired-token reset
        count.
        """
        encoded_id = quote(folder_id, safe="")
        query = urlencode({"$select": ",".join(self.discovery_fields)})
        return self._message_delta_request(
            self._mailbox_url(f"/mailFolders/{encoded_id}/messages/delta?{query}"),
            folder_id=folder_id,
            page_number=1,
            from_checkpoint=False,
            reset_count=reset_count,
        )

    def _message_delta_request(
        self,
        url: str,
        *,
        folder_id: str,
        page_number: int,
        from_checkpoint: bool = False,
        reset_count: int = 0,
    ) -> scrapy.Request:
        """
        Keep opaque delta URLs and bypass HTTP cache for every cursor request.

        Cache replay must never make an old delta round look current. Page size
        belongs in ``Prefer`` because Graph owns query parameters in
        continuation and delta links.
        """
        return self._request(
            url,
            callback=self.parse_message_delta,
            purpose="message-delta",
            cb_kwargs={
                "folder_id": folder_id,
                "page_number": page_number,
                "from_checkpoint": from_checkpoint,
                "reset_count": reset_count,
            },
            dont_cache=True,
            verbatim_url=(
                page_number > 1
                or from_checkpoint
                or "$deltatoken=" in url
                or "$skiptoken=" in url
            ),
            prefer=f'IdType="ImmutableId", odata.maxpagesize={self.page_size}',
        )
