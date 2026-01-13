"""Auto-generated custom processor."""

from __future__ import annotations

from typing import Any

from minidp import BaseMapProcessor, BaseProcessor, DataEntry, Record
from minidp.custom_processors import get_default_custom_registry


class AddPrefixProcessor(BaseMapProcessor):
    """
    Add a prefix to a specified field value.

    Params:
        field: Field name to modify
        prefix: Prefix to add
    """

    def __init__(
        self,
        field: str,
        prefix: str,
        **kwargs: Any,
    ) -> None:
        """Initialize AddPrefixProcessor."""
        super().__init__(**kwargs)
        self.field = field
        self.prefix = prefix

    def process_record(self, record: Record) -> list[DataEntry]:
        """Process a single record."""
        if self.field in record:
            record[self.field] = self.prefix + str(record[self.field])
        return [DataEntry(data=record)]


# Register the processor
get_default_custom_registry().register("AddPrefixProcessor", AddPrefixProcessor)
