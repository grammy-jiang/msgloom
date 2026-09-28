"""Layer application failure observation on reusable Graph log sanitization."""

from microsoft_graph.extensions.privacy import (
    MicrosoftGraphLogPrivacyExtension as GraphLogPrivacyExtension,
)

from ._logfilters import MicrosoftGraphScrapyPrivacyFilter


class MicrosoftGraphLogPrivacyExtension(GraphLogPrivacyExtension):
    """Preserve application integrity effects through the existing setting."""

    filter_class = MicrosoftGraphScrapyPrivacyFilter
