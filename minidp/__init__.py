"""
MiniDP - Minimal Data Processing Pipeline

A tiny, SDP-inspired data-processing spine that's modality-agnostic,
JSON-recipe-first, and easy for LLMs (and humans) to author/edit.

Basic usage:
    from minidp import run_recipe, PipelineRunner
    from minidp.recipe import load_recipe

    # Load and run a recipe
    recipe = load_recipe("my_recipe.json")
    output_path = run_recipe(recipe)

    # Or use PipelineRunner for more control
    runner = PipelineRunner(workspace_dir="./runs")
    output_path = runner.run_recipe(recipe)
    preview = runner.preview_recipe(recipe, n=5)
"""

__version__ = "0.1.0"

# Core types
from .types import DataEntry, Record, RunStats

# Manifest utilities
from .manifest import (
    count_records,
    is_nonempty_file,
    iter_jsonl,
    read_jsonl,
    write_jsonl,
)

# Processor base classes
from .processors_base import BaseMapProcessor, BaseProcessor

# Registry
from .registry import (
    ProcessorRegistry,
    get_default_registry,
    register_processor,
)

# Runner
from .runner import PipelineRunner, RunContext, run_recipe

# Recipe utilities
from .recipe import load_recipe, save_recipe, validate_recipe

# Errors
from .errors import (
    ConfigurationError,
    ManifestError,
    MiniDPError,
    ProcessorError,
    RecipeValidationError,
    RegistryError,
)

# Import common processors to register them
from . import processors  # noqa: F401

__all__ = [
    # Version
    "__version__",
    # Types
    "Record",
    "DataEntry",
    "RunStats",
    # Manifest
    "iter_jsonl",
    "write_jsonl",
    "read_jsonl",
    "is_nonempty_file",
    "count_records",
    # Base classes
    "BaseProcessor",
    "BaseMapProcessor",
    # Registry
    "ProcessorRegistry",
    "get_default_registry",
    "register_processor",
    # Runner
    "RunContext",
    "PipelineRunner",
    "run_recipe",
    # Recipe
    "load_recipe",
    "save_recipe",
    "validate_recipe",
    # Errors
    "MiniDPError",
    "RecipeValidationError",
    "ProcessorError",
    "RegistryError",
    "ManifestError",
    "ConfigurationError",
]
