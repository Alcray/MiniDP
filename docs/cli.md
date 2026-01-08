# CLI Reference

MiniDP provides a command-line interface for running and managing pipelines.

## Installation

After installing MiniDP, the `minidp` command is available:

```bash
pip install -e .
minidp --help
```

Alternatively, run as a module:

```bash
python -m cli.minidp --help
```

## Commands

### run

Execute a recipe.

```bash
minidp run <recipe.json> [options]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `recipe.json` | Path to the recipe file |

**Options:**

| Option | Description |
|--------|-------------|
| `-w, --workspace` | Override workspace directory |
| `--keep-temps` | Preserve temporary files after execution |

**Examples:**

```bash
# Basic execution
minidp run pipeline.json

# Custom workspace
minidp run pipeline.json --workspace ./output

# Debug with temp files
minidp run pipeline.json --keep-temps
```

### preview

Run a recipe and display the first N output records.

```bash
minidp preview <recipe.json> [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-n` | Number of records to display (default: 5) |
| `-w, --workspace` | Override workspace directory |

**Examples:**

```bash
# Preview first 5 records
minidp preview pipeline.json

# Preview first 10 records
minidp preview pipeline.json -n 10
```

### validate

Validate a recipe file without executing it.

```bash
minidp validate <recipe.json>
```

**Examples:**

```bash
minidp validate pipeline.json
```

Output:

```
Recipe 'pipeline.json' is valid.
  Name: my_pipeline
  Steps: 3
```

### list-processors

List all registered processors with descriptions.

```bash
minidp list-processors
```

Output:

```
Available processors:
  AddConstantFields: Add fixed fields to every record.
  DropSpecifiedFields: Remove specified fields from every record.
  DuplicateFields: Copy values from one field to another.
  FilterByField: Filter records based on a field value.
  KeepOnlySpecifiedFields: Keep only specified fields in every record.
  PassThrough: Pass records through unchanged.
  RenameFields: Rename fields in every record.
  SortManifest: Sort manifest by a specified attribute.
```

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Error (invalid recipe, execution failure, etc.) |

## Output

Pipeline execution logs to stdout with a run ID prefix:

```
[a1b2c3d4] Starting pipeline: my_pipeline
[a1b2c3d4] Running 3 step(s)
[a1b2c3d4] Running step 'step_1' (AddConstantFields)
[a1b2c3d4] [step_1] RunStats(in=100, out=100, dropped=0, expanded=0, time=0.01s)
...
[a1b2c3d4] Pipeline complete. Output: ./data/output.jsonl
```

## Scripting

For scripting, capture the output manifest path:

```bash
OUTPUT=$(minidp run pipeline.json | grep "Output manifest:" | cut -d' ' -f3)
echo "Results at: $OUTPUT"
```

Or use the Python API for programmatic control:

```python
from minidp import run_recipe, load_recipe

recipe = load_recipe("pipeline.json")
output_path = run_recipe(recipe)
```
