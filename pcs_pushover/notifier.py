"""Pushover notifier wrapper.

Provides a tiny helper around the Pushover REST API for sending messages.
"""

import os

import requests


class PushoverNotifier:
    """Send notifications to devices via Pushover.

    Credentials can be provided directly or read from environment variables
    ``PUSHOVER_TOKEN`` and ``PUSHOVER_USER``.
    """

    def __init__(self, token: str | None = None, user: str | None = None) -> None:
        """Initialize the notifier.

        Args:
            token: Pushover application token. Falls back to ``PUSHOVER_TOKEN``.
            user: Pushover user key. Falls back to ``PUSHOVER_USER``.

        Raises:
            ValueError: If credentials are missing.
        """
        self.token = token or os.getenv("PUSHOVER_TOKEN")
        self.user = user or os.getenv("PUSHOVER_USER")
        if not self.token or not self.user:
            raise ValueError(
                "Missing Pushover credentials: set PUSHOVER_TOKEN and PUSHOVER_USER"
            )

    def send(
        self,
        message: str,
        title: str | None = None,
        url: str | None = None,
        priority: int = 0,
    ) -> None:
        """Send a message via Pushover.

        Args:
            message: Message body. Trimmed to 1024 characters.
            title: Optional message title. Trimmed to 250 characters.
            url: Optional URL to attach to the notification.
            priority: Pushover priority; ``0`` by default.
        """
        payload = {
            "token": self.token,
            "user": self.user,
            "message": message[:1024],
        }
        if title:
            payload["title"] = title[:250]
        if url:
            payload["url"] = url
        if priority:
            payload["priority"] = str(priority)

        r = requests.post(
            "https://api.pushover.net/1/messages.json", data=payload, timeout=10
        )
        r.raise_for_status()
