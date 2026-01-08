# Configuration Guide

MiniDP uses JSON recipes to define data processing pipelines. This document covers the recipe format and configuration options.

## Recipe Format

A recipe is a JSON file with the following structure:

```json
{
  "version": "0.1",
  "name": "my_pipeline",
  "workspace_dir": "./runs/my_pipeline",
  "input_manifest": "./data/input.jsonl",
  "output_manifest": "./data/output.jsonl",
  "steps_to_run": "all",
  "steps": [
    {
      "id": "step_1",
      "type": "ProcessorName",
      "enabled": true,
      "params": {}
    }
  ]
}
```

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | No | Recipe format version. Current: `"0.1"` |
| `name` | string | No | Pipeline name for logging |
| `workspace_dir` | string | No | Base directory for outputs and temporary files. Default: `./runs` |
| `input_manifest` | string | No | Path to input JSONL manifest |
| `output_manifest` | string | No | Path to output JSONL manifest |
| `steps_to_run` | string | No | Which steps to execute. Default: `"all"` |
| `steps` | array | Yes | List of processor steps |

## Step Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | No | Unique identifier for the step (used in logging) |
| `type` | string | Yes | Processor name or import path |
| `enabled` | boolean | No | If `false`, skip this step. Default: `true` |
| `params` | object | No | Processor-specific parameters |
| `input_manifest` | string | No | Override input path for this step |
| `output_manifest` | string | No | Override output path for this step |

## Step Selection

The `steps_to_run` field controls which steps execute:

| Value | Description |
|-------|-------------|
| `"all"` | Run all steps (default) |
| `"2:"` | Run from step index 2 to end |
| `":3"` | Run from start to step index 3 (exclusive) |
| `"1:4"` | Run steps 1, 2, 3 |

Step indices are zero-based.

## I/O Stitching

When `input_manifest` or `output_manifest` are omitted from a step, MiniDP automatically connects steps:

1. First step uses recipe-level `input_manifest`
2. Intermediate steps use temporary files in `workspace_dir/.tmp/`
3. Last step writes to recipe-level `output_manifest`

This allows multi-step pipelines without manual path management.

## Manifest Format

Manifests use JSON Lines format (one JSON object per line):

```
{"id": 1, "text": "First record"}
{"id": 2, "text": "Second record"}
```

## Example Recipe

```json
{
  "version": "0.1",
  "name": "text_processing",
  "workspace_dir": "./runs/text_processing",
  "input_manifest": "./data/input.jsonl",
  "output_manifest": "./data/output.jsonl",
  "steps": [
    {
      "id": "add_metadata",
      "type": "AddConstantFields",
      "params": {
        "fields": {"source": "web", "version": "1.0"}
      }
    },
    {
      "id": "clean_fields",
      "type": "DropSpecifiedFields",
      "params": {
        "fields_to_drop": ["debug", "temp"]
      }
    },
    {
      "id": "normalize_names",
      "type": "RenameFields",
      "params": {
        "rename_fields": {"text": "content"}
      }
    }
  ]
}
```

## Python API

```python
from minidp import load_recipe, run_recipe, PipelineRunner

# Simple execution
recipe = load_recipe("recipe.json")
output_path = run_recipe(recipe)

# With options
runner = PipelineRunner(
    workspace_dir="./runs",
    keep_temps=True  # Preserve intermediate files
)
output_path = runner.run_recipe(recipe)

# Preview without full execution
records = runner.preview_recipe(recipe, n=5)
```
