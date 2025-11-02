"""Parsing and formatting helpers for IRC log lines."""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Optional

MIRC_COLOR = "\x03"
MIRC_BOLD = "\x02"
MIRC_ITALIC = "\x1d"
MIRC_UNDERLINE = "\x1f"
MIRC_RESET = "\x0f"
MIRC_MONOSPACE = "\x11"
MIRC_REVERSE = "\x16"


def strip_irc_formatting(s: str) -> str:
    s = re.sub(r"\x03(\d{1,2})(,\d{1,2})?", "", s)
    s = (
        s.replace(MIRC_BOLD, "")
        .replace(MIRC_ITALIC, "")
        .replace(MIRC_UNDERLINE, "")
        .replace(MIRC_RESET, "")
        .replace(MIRC_MONOSPACE, "")
        .replace(MIRC_REVERSE, "")
    )
    s = re.sub(r"[\x00-\x08\x0B-\x1A\x1C-\x1F]", "", s)
    return s


class Kind(str, enum.Enum):
    MESSAGE = "message"
    ACTION = "action"
    SYSTEM = "system"
    RAW = "raw"


@dataclass
class ParsedLine:
    timestamp: Optional[str]
    nick: Optional[str]
    text: str
    kind: Kind


PATTERN1 = re.compile(r"^\s*\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s+<([^>]+)>\s+(.*)$")
PATTERN2 = re.compile(
    r"^\s*\d{4}-\d{2}-\d{2}\s+(\d{1,2}:\d{2}(?::\d{2})?)\s+<([^>]+)>\s+(.*)$"
)
PATTERN3 = re.compile(r"^\s*\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s+\*\s+(\S+)\s+(.*)$")
PATTERN_SYS1 = re.compile(r"^\s*(?:\*\*\*|-->|<--|—>|<-)\s+(.*)$")
PATTERN_SYS2 = re.compile(r"^\s*-{2,}\s+(.*)$")


def parse_line(line: str) -> ParsedLine:
    """Parse a single log line into structured data."""
    raw = strip_irc_formatting(line.rstrip("\n"))
    m = PATTERN2.match(raw)
    if m:
        return ParsedLine(
            timestamp=m.group(1),
            nick=m.group(2),
            text=m.group(3),
            kind=Kind.MESSAGE,
        )
    m = PATTERN1.match(raw)
    if m:
        return ParsedLine(
            timestamp=m.group(1),
            nick=m.group(2),
            text=m.group(3),
            kind=Kind.MESSAGE,
        )
    m = PATTERN3.match(raw)
    if m:
        return ParsedLine(
            timestamp=m.group(1),
            nick=m.group(2),
            text=m.group(3),
            kind=Kind.ACTION,
        )
    m = PATTERN_SYS1.match(raw) or PATTERN_SYS2.match(raw)
    if m:
        return ParsedLine(timestamp=None, nick=None, text=m.group(1), kind=Kind.SYSTEM)
    m = re.match(r"^\s*<([^>]+)>\s+(.*)$", raw)
    if m:
        return ParsedLine(
            timestamp=None,
            nick=m.group(1),
            text=m.group(2),
            kind=Kind.MESSAGE,
        )
    return ParsedLine(
        timestamp=None,
        nick=None,
        text=raw,
        kind=Kind.RAW,
    )
