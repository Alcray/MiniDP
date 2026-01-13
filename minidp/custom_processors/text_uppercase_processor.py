"""Auto-generated custom processor."""

from __future__ import annotations

from typing import Any

from minidp import BaseMapProcessor, BaseProcessor, DataEntry, Record
from minidp.custom_processors import get_default_custom_registry


class TextUppercaseProcessor(BaseMapProcessor):
    """
    Convert a text field to uppercase.

    Params:
        field: Field name to convert to uppercase
        preserve_original: If True, keep original value in field_original
    """

    def __init__(
        self,
        field: str,
        preserve_original: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize TextUppercaseProcessor."""
        super().__init__(**kwargs)
        self.field = field
        self.preserve_original = preserve_original

    def process_record(self, record: Record) -> list[DataEntry]:
        """Process a single record."""
        if self.field in record:
            if self.preserve_original:
                record[f"{self.field}_original"] = record[self.field]
            record[self.field] = str(record[self.field]).upper()
        return [DataEntry(data=record)]


# Register the processor
get_default_custom_registry().register("TextUppercaseProcessor", TextUppercaseProcessor)
