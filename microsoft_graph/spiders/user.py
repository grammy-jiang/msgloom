"""Microsoft Graph signed-in user path and read permission."""

from typing import ClassVar

from .graph import MicrosoftGraphSpider


class MicrosoftGraphUserSpider(MicrosoftGraphSpider):
    """Supply user profile mechanics without output or persistence policy."""

    graph_permissions: ClassVar[tuple[str, ...]] = ("User.Read",)

    def user_path(self) -> str:
        """Address the signed-in user's profile."""
        return "/me"


__all__ = ["MicrosoftGraphUserSpider"]
