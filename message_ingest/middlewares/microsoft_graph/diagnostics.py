"""Compatibility settings for msgloom Graph transport diagnostics."""

import logging

from microsoft_graph.middlewares.diagnostics import (
    MicrosoftGraphDiagnosticsMiddleware as GraphDiagnosticsMiddleware,
)


class MicrosoftGraphDiagnosticsMiddleware(GraphDiagnosticsMiddleware):
    """Retain existing correlation metadata, statistics, and logger names."""

    client_request_id_meta = "_msgloom_ms_client_request_id"
    default_stats_prefix = "msgloom"
    logger = logging.getLogger(__name__)
