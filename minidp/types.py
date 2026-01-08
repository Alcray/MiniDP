"""Core type definitions for MiniDP."""

from dataclasses import dataclass, field
from typing import Any

# Type alias for a manifest record (must be JSON-serializable)
Record = dict[str, Any]


@dataclass
class DataEntry:
    """
    Wrapper for a record with optional metrics.

    Attributes:
        data: The record data, or None to signal this entry should be dropped.
              Setting data=None allows keeping metrics for dropped entries.
        metrics: Optional metrics dictionary for evaluation/debugging hooks.

    SDP semantics: if data is None, the entry is dropped from the output
    manifest but metrics can still be collected.
    """

    data: Record | None
    metrics: dict[str, Any] = field(default_factory=dict)

    def should_drop(self) -> bool:
        """Return True if this entry should be dropped (data is None)."""
        return self.data is None


@dataclass
class RunStats:
    """
    Statistics collected during a processor run.

    Attributes:
        num_in: Number of input records processed.
        num_out: Number of output records written.
        dropped: Number of entries dropped (data=None or empty list returned).
        expanded: Count of cases where 1 input produced >1 output.
        wall_time_s: Wall clock time in seconds for the processor run.
    """

    num_in: int = 0
    num_out: int = 0
    dropped: int = 0
    expanded: int = 0
    wall_time_s: float = 0.0

    def __str__(self) -> str:
        return (
            f"RunStats(in={self.num_in}, out={self.num_out}, "
            f"dropped={self.dropped}, expanded={self.expanded}, "
            f"time={self.wall_time_s:.2f}s)"
        )
