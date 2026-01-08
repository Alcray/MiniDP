# MiniDP

A minimal, JSON-recipe-first data processing pipeline inspired by [NVIDIA NeMo SDP](https://nvidia.github.io/NeMo-speech-data-processor/).

MiniDP provides a lightweight, modality-agnostic spine for building data transformation pipelines. It is designed to be easily authored and edited by both humans and LLMs.

## Features

- Deterministic execution engine
- JSON recipe format (tool-calling friendly, human editable)
- Streaming JSONL manifest processing
- Composable processor API with drop/modify/expand semantics
- Optional multiprocessing support
- Zero external dependencies (stdlib only)

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Run a pipeline
minidp run examples/demo_recipe.json

# Preview output
minidp preview examples/demo_recipe.json -n 5

# List available processors
minidp list-processors
```

## Documentation

- [Configuration Guide](docs/configuration.md) - Recipe format and options
- [Processors Guide](docs/processors.md) - Built-in processors and creating custom ones
- [CLI Reference](docs/cli.md) - Command-line interface

## License

MIT
