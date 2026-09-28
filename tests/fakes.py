"""Test doubles shared across the suite. None of these are full LangChain
Runnables — each mimics only the one method (`.invoke`) the code under test
actually calls, which is deliberate: it keeps tests from silently depending
on LangChain internals."""

from __future__ import annotations

from typing import Any


class FakeInvokable:
    def __init__(self, result: Any) -> None:
        self._result = result
        self.last_inputs: Any = None

    def invoke(self, inputs: Any) -> Any:
        self.last_inputs = inputs
        return self._result


class FakeMessage:
    """Stands in for a LangChain AIMessage — the code under test only reads
    `.content`."""

    def __init__(self, content: str) -> None:
        self.content = content
