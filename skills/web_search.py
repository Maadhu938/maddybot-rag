"""Placeholder for an offline web search capability.

This module currently stubs out the interface that other components can
call once an offline search index or retrieval system is available.
"""

from typing import Optional


class WebSearchSkill:
    """Stub skill to illustrate how external tools can be attached."""

    def run(self, query: str) -> Optional[str]:
        """Return a placeholder response until a real search backend exists."""
        sanitized_query = query.strip()
        if not sanitized_query:
            return None
        return (
            "[web_search] No offline search index is configured yet. "
            "Add one to enable knowledge lookups."
        )
