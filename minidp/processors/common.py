"""Generic built-in processors for MiniDP.

These processors are data-agnostic and work with any manifest format.
They mirror the "miscellaneous" processors from SDP but without
modality-specific assumptions.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ..manifest import iter_jsonl, write_jsonl
from ..processors_base import BaseMapProcessor, BaseProcessor
from ..registry import register_processor
from ..types import DataEntry, Record, RunStats

if True:  # TYPE_CHECKING workaround for runtime registration
    from ..runner import RunContext


@register_processor("AddConstantFields")
class AddConstantFields(BaseMapProcessor):
    """
    Add fixed fields to every record.

    Params:
        fields: Dictionary of field names to constant values.

    Example:
        {"type": "AddConstantFields", "params": {"fields": {"source": "web"}}}
    """

    def __init__(
        self,
        fields: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.fields = fields

    def process_record(self, record: Record) -> list[DataEntry]:
        new_record = record.copy()
        for key, value in self.fields.items():
            new_record[key] = value
        return [DataEntry(data=new_record)]


@register_processor("DropSpecifiedFields")
class DropSpecifiedFields(BaseMapProcessor):
    """
    Remove specified fields from every record.

    Params:
        fields_to_drop: List of field names to remove.

    Example:
        {"type": "DropSpecifiedFields", "params": {"fields_to_drop": ["debug", "temp"]}}
    """

    def __init__(
        self,
        fields_to_drop: list[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.fields_to_drop = set(fields_to_drop)

    def process_record(self, record: Record) -> list[DataEntry]:
        new_record = {
            k: v for k, v in record.items() if k not in self.fields_to_drop
        }
        return [DataEntry(data=new_record)]


@register_processor("KeepOnlySpecifiedFields")
class KeepOnlySpecifiedFields(BaseMapProcessor):
    """
    Keep only specified fields in every record.

    Params:
        fields_to_keep: List of field names to retain.

    Example:
        {"type": "KeepOnlySpecifiedFields", "params": {"fields_to_keep": ["id", "text"]}}
    """

    def __init__(
        self,
        fields_to_keep: list[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.fields_to_keep = set(fields_to_keep)

    def process_record(self, record: Record) -> list[DataEntry]:
        new_record = {
            k: v for k, v in record.items() if k in self.fields_to_keep
        }
        return [DataEntry(data=new_record)]


@register_processor("RenameFields")
class RenameFields(BaseMapProcessor):
    """
    Rename fields in every record.

    Params:
        rename_fields: Dictionary mapping old names to new names.

    Example:
        {"type": "RenameFields", "params": {"rename_fields": {"old_name": "new_name"}}}
    """

    def __init__(
        self,
        rename_fields: dict[str, str],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.rename_fields = rename_fields

    def process_record(self, record: Record) -> list[DataEntry]:
        new_record = {}
        for key, value in record.items():
            new_key = self.rename_fields.get(key, key)
            new_record[new_key] = value
        return [DataEntry(data=new_record)]


@register_processor("DuplicateFields")
class DuplicateFields(BaseMapProcessor):
    """
    Copy values from one field to another (duplicate fields).

    Params:
        duplicate_fields: Dictionary mapping source fields to target fields.

    Example:
        {"type": "DuplicateFields", "params": {"duplicate_fields": {"text": "text_backup"}}}
    """

    def __init__(
        self,
        duplicate_fields: dict[str, str],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.duplicate_fields = duplicate_fields

    def process_record(self, record: Record) -> list[DataEntry]:
        new_record = record.copy()
        for source, target in self.duplicate_fields.items():
            if source in new_record:
                new_record[target] = new_record[source]
        return [DataEntry(data=new_record)]


@register_processor("SortManifest")
class SortManifest(BaseProcessor):
    """
    Sort manifest by a specified attribute.

    Note: This processor loads all records into memory for sorting.
    Use BaseProcessor (not BaseMapProcessor) since sorting is not streaming.

    Params:
        attribute_sort_by: Field name to sort by.
        descending: If True, sort in descending order. Default True.

    Example:
        {"type": "SortManifest", "params": {"attribute_sort_by": "score", "descending": true}}
    """

    def __init__(
        self,
        attribute_sort_by: str,
        descending: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.attribute_sort_by = attribute_sort_by
        self.descending = descending

    def process(self, ctx: RunContext) -> str:
        from ..errors import ProcessorError

        if self.output_manifest is None:
            raise ProcessorError(
                f"Processor '{self.name}' has no output_manifest set"
            )

        # Ensure output directory exists
        Path(self.output_manifest).parent.mkdir(parents=True, exist_ok=True)

        self.prepare(ctx)

        start_time = time.perf_counter()

        # Read all records into memory
        records: list[Record] = []
        if self.input_manifest:
            records = list(iter_jsonl(self.input_manifest))

        num_in = len(records)

        # Sort by attribute
        def sort_key(r: Record) -> Any:
            return r.get(self.attribute_sort_by)

        records.sort(key=sort_key, reverse=self.descending)

        # Write sorted records
        write_jsonl(self.output_manifest, records)

        wall_time = time.perf_counter() - start_time

        stats = RunStats(
            num_in=num_in,
            num_out=len(records),
            dropped=0,
            expanded=0,
            wall_time_s=wall_time,
        )

        ctx.log(f"[{self.name}] {stats}")

        self.finalize(ctx, stats)

        return self.output_manifest


@register_processor("FilterByField")
class FilterByField(BaseMapProcessor):
    """
    Filter records based on a field value.

    Params:
        field: Field name to check.
        values: List of allowed values. Records with field value in this list are kept.
        exclude: If True, exclude records with matching values instead. Default False.

    Example:
        {"type": "FilterByField", "params": {"field": "lang", "values": ["en", "es"]}}
    """

    def __init__(
        self,
        field: str,
        values: list[Any],
        exclude: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.field = field
        self.values = set(values)
        self.exclude = exclude

    def process_record(self, record: Record) -> list[DataEntry]:
        field_value = record.get(self.field)
        matches = field_value in self.values

        if self.exclude:
            # Drop if matches
            if matches:
                return []
            return [DataEntry(data=record)]
        else:
            # Keep if matches
            if matches:
                return [DataEntry(data=record)]
            return []


@register_processor("PassThrough")
class PassThrough(BaseMapProcessor):
    """
    Pass records through unchanged. Useful for testing or as a no-op placeholder.

    Example:
        {"type": "PassThrough", "params": {}}
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def process_record(self, record: Record) -> list[DataEntry]:
        return [DataEntry(data=record)]
