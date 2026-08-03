"""Shared string coercions for API schemas."""

from __future__ import annotations

import html
from typing import Annotated

from pydantic import BeforeValidator


def _unescape(value: object) -> object:
    if isinstance(value, str):
        return html.unescape(value)
    return value


UnescapedStr = Annotated[str, BeforeValidator(_unescape)]
