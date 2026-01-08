# Processors Guide

Processors are the building blocks of MiniDP pipelines. This document covers built-in processors and how to create custom ones.

## Built-in Processors

### AddConstantFields

Adds fixed fields to every record.

```json
{
  "type": "AddConstantFields",
  "params": {
    "fields": {"source": "web", "version": "1.0"}
  }
}
```

### DropSpecifiedFields

Removes specified fields from every record.

```json
{
  "type": "DropSpecifiedFields",
  "params": {
    "fields_to_drop": ["debug", "temp", "internal_id"]
  }
}
```

### KeepOnlySpecifiedFields

Keeps only the specified fields, removing all others.

```json
{
  "type": "KeepOnlySpecifiedFields",
  "params": {
    "fields_to_keep": ["id", "text", "label"]
  }
}
```

### RenameFields

Renames fields in every record.

```json
{
  "type": "RenameFields",
  "params": {
    "rename_fields": {"old_name": "new_name", "text": "content"}
  }
}
```

### DuplicateFields

Copies field values to new fields.

```json
{
  "type": "DuplicateFields",
  "params": {
    "duplicate_fields": {"text": "text_backup", "id": "original_id"}
  }
}
```

### FilterByField

Filters records based on field values.

```json
{
  "type": "FilterByField",
  "params": {
    "field": "lang",
    "values": ["en", "es"],
    "exclude": false
  }
}
```

Set `exclude: true` to drop records that match instead of keeping them.

### SortManifest

Sorts the manifest by a specified field. Loads all records into memory.

```json
{
  "type": "SortManifest",
  "params": {
    "attribute_sort_by": "score",
    "descending": true
  }
}
```

### PassThrough

Passes records unchanged. Useful for testing or as a placeholder.

```json
{
  "type": "PassThrough",
  "params": {}
}
```

## Creating Custom Processors

### Basic Structure

```python
from minidp import BaseMapProcessor, DataEntry, register_processor

@register_processor("MyProcessor")
class MyProcessor(BaseMapProcessor):
    def __init__(self, my_param: str, **kwargs):
        super().__init__(**kwargs)
        self.my_param = my_param

    def process_record(self, record: dict) -> list[DataEntry]:
        new_record = record.copy()
        new_record["processed"] = self.my_param
        return [DataEntry(data=new_record)]
```

### Return Semantics

The `process_record` method returns a list of `DataEntry` objects:

| Return Value | Behavior |
|--------------|----------|
| `[]` | Drop the record |
| `[DataEntry(data=record)]` | Pass through or modify |
| `[DataEntry(data=r1), DataEntry(data=r2)]` | Expand into multiple records |
| `[DataEntry(data=None)]` | Drop but preserve metrics |

### Example: Filter Processor

```python
@register_processor("LengthFilter")
class LengthFilter(BaseMapProcessor):
    def __init__(self, field: str, min_length: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.field = field
        self.min_length = min_length

    def process_record(self, record: dict) -> list[DataEntry]:
        value = record.get(self.field, "")
        if len(str(value)) < self.min_length:
            return []  # Drop
        return [DataEntry(data=record)]
```

### Example: Expand Processor

```python
@register_processor("SplitByDelimiter")
class SplitByDelimiter(BaseMapProcessor):
    def __init__(self, field: str, delimiter: str = ",", **kwargs):
        super().__init__(**kwargs)
        self.field = field
        self.delimiter = delimiter

    def process_record(self, record: dict) -> list[DataEntry]:
        value = record.get(self.field, "")
        parts = str(value).split(self.delimiter)
        
        results = []
        for i, part in enumerate(parts):
            new_record = record.copy()
            new_record[self.field] = part.strip()
            new_record["split_index"] = i
            results.append(DataEntry(data=new_record))
        return results
```

### Parallel Processing

Enable multiprocessing by setting `max_workers`:

```json
{
  "type": "MyProcessor",
  "params": {
    "max_workers": 4,
    "in_memory_chunksize": 10000
  }
}
```

When using parallel processing, `process_record` must be pure (no side effects on processor instance state).

### Using Import Paths

Processors can be referenced by import path instead of registration:

```json
{
  "type": "mypackage.processors.MyProcessor",
  "params": {}
}
```

### Base Classes

MiniDP provides two base classes:

| Class | Use Case |
|-------|----------|
| `BaseMapProcessor` | Record-by-record transformations (most common) |
| `BaseProcessor` | Custom I/O or global operations (e.g., sorting) |

For `BaseProcessor`, implement the `process(ctx) -> str` method directly.

### Lifecycle Hooks

Both base classes support optional hooks:

```python
def prepare(self, ctx: RunContext) -> None:
    """Called before processing. Load models, validate paths, etc."""
    pass

def finalize(self, ctx: RunContext, stats: RunStats) -> None:
    """Called after processing. Cleanup, logging, etc."""
    pass
```

## DataEntry and Metrics

`DataEntry` includes a `metrics` field for evaluation data:

```python
def process_record(self, record: dict) -> list[DataEntry]:
    new_record = record.copy()
    metrics = {"original_length": len(record.get("text", ""))}
    return [DataEntry(data=new_record, metrics=metrics)]
```

Metrics are preserved even when `data=None` (dropped records), enabling analysis of filtered data.
