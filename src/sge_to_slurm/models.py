from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LineStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    NEUTRAL = "neutral"


class LineKind(str, Enum):
    SHEBANG = "shebang"
    SGE_DIRECTIVE = "sge_directive"
    COMMENT = "comment"
    BLANK = "blank"
    BODY = "body"


@dataclass
class LineReport:
    """Structured result for one input line (for tests and Rich)."""

    line_no: int
    kind: LineKind
    status: LineStatus
    source: str
    message: str = ""
    emitted: list[str] = field(default_factory=list)


@dataclass
class ConversionResult:
    output_text: str
    lines: list[LineReport]
    output_path: str | None

    @property
    def counts(self) -> tuple[int, int, int]:
        ok = sum(1 for r in self.lines if r.status == LineStatus.OK)
        warn = sum(1 for r in self.lines if r.status == LineStatus.WARNING)
        err = sum(1 for r in self.lines if r.status == LineStatus.ERROR)
        return ok, warn, err
