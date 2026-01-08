"""JSONL manifest read/write utilities."""

import json
import os
from collections.abc import Iterable, Iterator
from pathlib import Path

from .errors import ManifestError
from .types import Record


def iter_jsonl(path: str | Path) -> Iterator[Record]:
    """
    Iterate over records in a JSONL file.

    Args:
        path: Path to the JSONL file.

    Yields:
        Record dictionaries, one per non-empty line.

    Note:
        If the file doesn't exist or is empty, yields nothing
        (manifest creation mode behavior per SDP semantics).
    """
    path = Path(path)

    if not path.exists():
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    raise ManifestError(
                        f"Invalid JSON at {path}:{line_num}: {e}"
                    ) from e
    except OSError as e:
        raise ManifestError(f"Failed to read manifest {path}: {e}") from e


def write_jsonl(path: str | Path, records: Iterable[Record]) -> int:
    """
    Write records to a JSONL file.

    Args:
        path: Path to the output JSONL file.
        records: Iterable of record dictionaries.

    Returns:
        Number of records written.

    Raises:
        ManifestError: If writing fails.
    """
    path = Path(path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    try:
        with open(path, "w", encoding="utf-8") as f:
            for record in records:
                json.dump(record, f, ensure_ascii=False, separators=(",", ":"))
                f.write("\n")
                count += 1
    except (OSError, TypeError) as e:
        raise ManifestError(f"Failed to write manifest {path}: {e}") from e

    return count


def is_nonempty_file(path: str | Path) -> bool:
    """
    Check if a file exists and has content.

    Args:
        path: Path to check.

    Returns:
        True if file exists and has size > 0, False otherwise.
    """
    path = Path(path)
    return path.exists() and path.stat().st_size > 0


def count_records(path: str | Path) -> int:
    """
    Count records in a JSONL file without loading all into memory.

    Args:
        path: Path to the JSONL file.

    Returns:
        Number of non-empty lines (records) in the file.
    """
    count = 0
    for _ in iter_jsonl(path):
        count += 1
    return count


def read_jsonl(path: str | Path) -> list[Record]:
    """
    Read all records from a JSONL file into a list.

    Args:
        path: Path to the JSONL file.

    Returns:
        List of all records.

    Note:
        For large files, prefer iter_jsonl for streaming.
    """
    return list(iter_jsonl(path))
