"""Offline skill that reports the current local time."""

from datetime import datetime


class TimeTool:
    """Provides human-readable timestamps for the agent."""

    def run(self) -> str:
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
