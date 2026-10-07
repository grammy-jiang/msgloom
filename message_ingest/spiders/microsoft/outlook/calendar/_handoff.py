"""Create content-free Calendar terminal proof after serial callback output."""

import json


def traversal_scope(spider):
    """Bind mailbox, source, and configured inventory or exact window scope."""
    scope = {
        "source_id": spider.crawler.settings.get("MSGLOOM_SOURCE_ID"),
        "mailbox": spider.target_mailbox or "me",
        "page_size": spider.page_size,
    }
    if spider.name == "outlook_calendar_window":
        scope.update(
            calendar_id=spider.calendar_id or "default",
            start_datetime=spider.start_datetime,
            end_datetime=spider.end_datetime,
        )
    return json.dumps(scope, sort_keys=True, separators=(",", ":"))


def terminal_completion(spider, evidence):
    """
    Return serializable proof only after all page observations were yielded.

    The configured serial callback output awaits raw persistence and canonical
    aliasing before iteration reaches this marker. No raw content or request
    object enters SpiderState. Failures still block release at native idle.
    """
    return {
        "run_id": spider.run_id,
        "scope": traversal_scope(spider),
        "evidence_id": evidence.evidence_id,
    }
