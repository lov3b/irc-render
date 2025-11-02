"""IRC log parsing pipeline."""

from typing import Iterator

from .formatting import ParsedLine, parse_line


class IRCLogParser:
    """Yield parsed log lines from a text file."""

    def parse_file(self, path: str) -> Iterator[ParsedLine]:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                yield parse_line(raw)
