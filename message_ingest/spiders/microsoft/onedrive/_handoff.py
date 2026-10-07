"""Bind attempt-local OneDrive completion to its exact source and target."""

import json


def discovery_scope(spider):
    """Identify the configured signed-in drive and root inventory scope."""
    return json.dumps(
        {
            "source_id": spider.crawler.settings.get("MSGLOOM_SOURCE_ID"),
            "graph_root": spider.graph_root,
            "drive_id": spider.handoff_drive_id,
            "page_size": spider.page_size,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def completion(spider, evidence, scope):
    """
    Record canonical evidence after serial callback output has drained.

    OneDrive rejects JOBDIR. These primitive markers describe this attempt
    only and cannot grant resume support. Pipeline errors still block release.
    """
    return {
        "run_id": spider.run_id,
        "source_id": spider.crawler.settings.get("MSGLOOM_SOURCE_ID"),
        "scope": scope,
        "evidence_id": evidence.evidence_id,
    }
