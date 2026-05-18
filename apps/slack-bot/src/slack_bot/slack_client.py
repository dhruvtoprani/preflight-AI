from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SlackMessageResult:
    channel: str
    ts: str


class SlackMessenger:
    def __init__(self, client=None) -> None:
        if client is not None:
            self.client = client
            return

        try:
            from slack_sdk import WebClient  # imported lazily for optional runtime dependency
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "slack_sdk is required for live Slack messaging. Install slack-sdk to enable this path."
            ) from exc

        self.client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

    def post_message(self, channel: str, text: str, thread_ts: str | None = None) -> SlackMessageResult:
        response = self.client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)
        return SlackMessageResult(channel=response["channel"], ts=response["ts"])
