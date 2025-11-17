"""Placeholder sandbox for running user-supplied code snippets locally."""

from typing import Optional


class CodeRunnerSkill:
    """Stub that prevents execution until a trusted sandbox is available."""

    def run(self, code: str) -> Optional[str]:
        _ = code  # Mark parameter as used for static analyzers.
        return (
            "[code_runner] Execution disabled. Integrate a secure sandbox to run code."  # noqa: E501
        )
