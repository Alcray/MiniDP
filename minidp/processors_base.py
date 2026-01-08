"""Base processor classes for MiniDP."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .errors import ConfigurationError, ProcessorError
from .manifest import is_nonempty_file, iter_jsonl, write_jsonl
from .types import DataEntry, Record, RunStats

if TYPE_CHECKING:
    from .runner import RunContext


class BaseProcessor(ABC):
    """
    Base class for all processors.

    Processors that need custom I/O or operate globally should subclass this
    directly. For the common case of record-by-record transformation, use
    BaseMapProcessor instead.

    Attributes:
        input_manifest: Path to input manifest file (optional).
        output_manifest: Path to output manifest file (required at runtime).
        enabled: Whether this processor should run (for recipe filtering).
        name: Optional name for logging/debugging.

    SDP constraint: input_manifest and output_manifest must not be equal
    when both are specified.
    """

    def __init__(
        self,
        input_manifest: str | None = None,
        output_manifest: str | None = None,
        enabled: bool = True,
        name: str | None = None,
    ) -> None:
        """
        Initialize the processor.

        Args:
            input_manifest: Path to input manifest (optional).
            output_manifest: Path to output manifest (required at runtime).
            enabled: Whether this processor is enabled.
            name: Optional name for logging.

        Raises:
            ConfigurationError: If input_manifest equals output_manifest.
        """
        if (
            input_manifest is not None
            and output_manifest is not None
            and input_manifest == output_manifest
        ):
            raise ConfigurationError(
                f"input_manifest and output_manifest must not be equal: "
                f"'{input_manifest}'"
            )

        self.input_manifest = input_manifest
        self.output_manifest = output_manifest
        self.enabled = enabled
        self.name = name or self.__class__.__name__

    def prepare(self, ctx: RunContext) -> None:
        """
        Optional hook called before processing.

        Override to perform setup like loading models, validating paths, etc.

        Args:
            ctx: The run context with workspace info and logging.
        """
        pass

    def finalize(self, ctx: RunContext, stats: RunStats) -> None:
        """
        Optional hook called after processing completes.

        Override to perform cleanup or log final statistics.

        Args:
            ctx: The run context.
            stats: Statistics from the processor run.
        """
        pass

    @abstractmethod
    def process(self, ctx: RunContext) -> str:
        """
        Execute the processor.

        Args:
            ctx: The run context with workspace info and logging.

        Returns:
            Path to the output manifest.

        Raises:
            ProcessorError: If processing fails.
        """
        pass


class BaseMapProcessor(BaseProcessor):
    """
    Base class for record-by-record transformation processors.

    This is the common case: read JSONL → transform each record → write JSONL.
    Subclasses implement process_record() which returns a list of DataEntry:
    - Empty list: drop the record
    - Single entry: modify/pass through
    - Multiple entries: expand/split one record into many

    Supports optional multiprocessing via max_workers parameter.

    Important: In multiprocessing mode, process_record must be pure with
    respect to processor instance state. Mutating shared attributes inside
    parallel mapping has undefined behavior.
    """

    def __init__(
        self,
        input_manifest: str | None = None,
        output_manifest: str | None = None,
        enabled: bool = True,
        name: str | None = None,
        max_workers: int = 0,
        in_memory_chunksize: int = 10_000,
    ) -> None:
        """
        Initialize the map processor.

        Args:
            input_manifest: Path to input manifest (optional).
            output_manifest: Path to output manifest (required at runtime).
            enabled: Whether this processor is enabled.
            name: Optional name for logging.
            max_workers: Number of worker processes. 0 means sequential.
            in_memory_chunksize: Chunk size for multiprocessing batches.
        """
        super().__init__(input_manifest, output_manifest, enabled, name)
        self.max_workers = max_workers
        self.in_memory_chunksize = in_memory_chunksize

    @abstractmethod
    def process_record(self, record: Record) -> list[DataEntry]:
        """
        Transform a single record.

        Args:
            record: The input record dictionary.

        Returns:
            List of DataEntry objects:
            - Empty list: drop the record
            - Single entry: modify/pass through
            - Multiple entries: expand into multiple output records

        Note:
            Return DataEntry(data=None) to drop but preserve metrics.
            In multiprocessing mode, this method must be pure (no side effects
            on processor instance state).
        """
        pass

    def read_records(self) -> Iterator[Record]:
        """
        Read records from the input manifest.

        Yields:
            Record dictionaries from the input manifest.

        Note:
            If input_manifest is missing or empty, yields nothing
            (manifest creation mode per SDP semantics).
        """
        if self.input_manifest is None:
            return

        if not is_nonempty_file(self.input_manifest):
            return

        yield from iter_jsonl(self.input_manifest)

    def write_entries(self, entries: Iterator[DataEntry]) -> RunStats:
        """
        Write entries to the output manifest.

        Only writes entries where data is not None.

        Args:
            entries: Iterator of DataEntry objects.

        Returns:
            RunStats with counts of processed entries.
        """
        if self.output_manifest is None:
            raise ProcessorError("output_manifest must be set before writing")

        stats = RunStats()

        def record_generator() -> Iterator[Record]:
            for entry in entries:
                if entry.data is not None:
                    stats.num_out += 1
                    yield entry.data

        write_jsonl(self.output_manifest, record_generator())
        return stats

    def _process_sequential(self, ctx: RunContext) -> RunStats:
        """Process records sequentially."""
        stats = RunStats()

        def entry_generator() -> Iterator[DataEntry]:
            for record in self.read_records():
                stats.num_in += 1
                try:
                    results = self.process_record(record)
                except Exception as e:
                    raise ProcessorError(
                        f"Error processing record {stats.num_in}: {e}"
                    ) from e

                if not results:
                    stats.dropped += 1
                    continue

                if len(results) > 1:
                    stats.expanded += 1

                for entry in results:
                    if entry.should_drop():
                        stats.dropped += 1
                    else:
                        yield entry

        write_stats = self.write_entries(entry_generator())
        stats.num_out = write_stats.num_out
        return stats

    def _process_parallel(self, ctx: RunContext) -> RunStats:
        """Process records in parallel using multiprocessing."""
        from .parallel import process_parallel

        return process_parallel(
            processor=self,
            ctx=ctx,
            max_workers=self.max_workers,
            chunksize=self.in_memory_chunksize,
        )

    def process(self, ctx: RunContext) -> str:
        """
        Execute the map processor.

        Args:
            ctx: The run context.

        Returns:
            Path to the output manifest.

        Raises:
            ProcessorError: If output_manifest is not set or processing fails.
        """
        if self.output_manifest is None:
            raise ProcessorError(
                f"Processor '{self.name}' has no output_manifest set"
            )

        # Ensure output directory exists
        Path(self.output_manifest).parent.mkdir(parents=True, exist_ok=True)

        # Call prepare hook
        self.prepare(ctx)

        # Time the processing
        start_time = time.perf_counter()

        try:
            if self.max_workers > 0:
                stats = self._process_parallel(ctx)
            else:
                stats = self._process_sequential(ctx)
        except ProcessorError:
            raise
        except Exception as e:
            raise ProcessorError(f"Processor '{self.name}' failed: {e}") from e

        stats.wall_time_s = time.perf_counter() - start_time

        # Log stats
        ctx.log(f"[{self.name}] {stats}")

        # Call finalize hook
        self.finalize(ctx, stats)

        return self.output_manifest
