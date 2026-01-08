"""Multiprocessing backend for MiniDP."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import TYPE_CHECKING

from .manifest import iter_jsonl, write_jsonl
from .types import DataEntry, Record, RunStats

if TYPE_CHECKING:
    from .processors_base import BaseMapProcessor
    from .runner import RunContext


def _apply_process_record(
    args: tuple[BaseMapProcessor, Record],
) -> list[DataEntry]:
    """
    Worker function for parallel processing.

    Args:
        args: Tuple of (processor, record).

    Returns:
        List of DataEntry results from process_record.
    """
    processor, record = args
    return processor.process_record(record)


def _chunk_iterator(records, chunksize: int):
    """
    Yield chunks of records.

    Args:
        records: Iterator of records.
        chunksize: Maximum size of each chunk.

    Yields:
        Lists of records, each up to chunksize.
    """
    chunk = []
    for record in records:
        chunk.append(record)
        if len(chunk) >= chunksize:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def process_parallel(
    processor: BaseMapProcessor,
    ctx: RunContext,
    max_workers: int,
    chunksize: int,
) -> RunStats:
    """
    Process records in parallel using ProcessPoolExecutor.

    Args:
        processor: The map processor instance.
        ctx: Run context.
        max_workers: Number of worker processes.
        chunksize: Size of chunks to process together.

    Returns:
        RunStats with processing statistics.

    Note:
        The processor's process_record method must be pure (no side effects
        on processor instance state) for parallel execution to work correctly.
    """
    from .errors import ProcessorError

    if processor.output_manifest is None:
        raise ProcessorError("output_manifest must be set")

    if processor.input_manifest is None:
        # No input - write empty output
        write_jsonl(processor.output_manifest, [])
        return RunStats()

    stats = RunStats()
    all_output_records: list[Record] = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Process in chunks to balance memory vs overhead
        for chunk in _chunk_iterator(
            iter_jsonl(processor.input_manifest), chunksize
        ):
            # Create args for each record in the chunk
            args_list = [(processor, record) for record in chunk]

            # Map process_record over the chunk
            try:
                results = list(executor.map(_apply_process_record, args_list))
            except Exception as e:
                raise ProcessorError(f"Parallel processing failed: {e}") from e

            # Process results maintaining order
            for record, entries in zip(chunk, results):
                stats.num_in += 1

                if not entries:
                    stats.dropped += 1
                    continue

                if len(entries) > 1:
                    stats.expanded += 1

                for entry in entries:
                    if entry.should_drop():
                        stats.dropped += 1
                    elif entry.data is not None:
                        all_output_records.append(entry.data)

    # Write all output records
    stats.num_out = len(all_output_records)
    write_jsonl(processor.output_manifest, all_output_records)

    return stats
