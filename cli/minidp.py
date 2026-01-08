#!/usr/bin/env python3
"""MiniDP command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_run(args: argparse.Namespace) -> int:
    """Run a recipe."""
    from minidp.recipe import load_recipe
    from minidp.runner import PipelineRunner

    try:
        recipe = load_recipe(args.recipe)
    except Exception as e:
        print(f"Error loading recipe: {e}", file=sys.stderr)
        return 1

    runner = PipelineRunner(
        workspace_dir=args.workspace or recipe.get("workspace_dir", "./runs"),
        keep_temps=args.keep_temps,
    )

    try:
        output_path = runner.run_recipe(recipe)
        print(f"\nOutput manifest: {output_path}")
        return 0
    except Exception as e:
        print(f"Error running recipe: {e}", file=sys.stderr)
        return 1


def cmd_preview(args: argparse.Namespace) -> int:
    """Preview recipe output."""
    from minidp.recipe import load_recipe
    from minidp.runner import PipelineRunner

    try:
        recipe = load_recipe(args.recipe)
    except Exception as e:
        print(f"Error loading recipe: {e}", file=sys.stderr)
        return 1

    runner = PipelineRunner(
        workspace_dir=args.workspace or recipe.get("workspace_dir", "./runs"),
        keep_temps=False,
    )

    try:
        records = runner.preview_recipe(recipe, n=args.n)

        if not records:
            print("No output records.")
            return 0

        print(f"\nFirst {len(records)} record(s):\n")
        for i, record in enumerate(records, 1):
            print(f"--- Record {i} ---")
            print(json.dumps(record, indent=2, ensure_ascii=False))
            print()

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a recipe file."""
    from minidp.recipe import load_recipe

    try:
        recipe = load_recipe(args.recipe)
        print(f"Recipe '{args.recipe}' is valid.")
        print(f"  Name: {recipe.get('name', 'unnamed')}")
        print(f"  Steps: {len(recipe.get('steps', []))}")
        return 0
    except Exception as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return 1


def cmd_list_processors(args: argparse.Namespace) -> int:
    """List available processors."""
    from minidp.registry import get_default_registry

    # Import common processors to ensure they're registered
    import minidp.processors.common  # noqa: F401

    registry = get_default_registry()
    processors = registry.list_processors()

    if not processors:
        print("No processors registered.")
        return 0

    print("Available processors:")
    for name in sorted(processors):
        cls = registry.get(name)
        doc = cls.__doc__ or "No description"
        # Get first line of docstring
        first_line = doc.strip().split("\n")[0]
        print(f"  {name}: {first_line}")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="minidp",
        description="MiniDP - Minimal Data Processing Pipeline",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # run command
    run_parser = subparsers.add_parser("run", help="Run a recipe")
    run_parser.add_argument("recipe", type=str, help="Path to recipe JSON file")
    run_parser.add_argument(
        "--workspace", "-w", type=str, help="Override workspace directory"
    )
    run_parser.add_argument(
        "--keep-temps", action="store_true", help="Keep temporary files"
    )
    run_parser.set_defaults(func=cmd_run)

    # preview command
    preview_parser = subparsers.add_parser(
        "preview", help="Preview recipe output (first N records)"
    )
    preview_parser.add_argument(
        "recipe", type=str, help="Path to recipe JSON file"
    )
    preview_parser.add_argument(
        "-n", type=int, default=5, help="Number of records to preview (default: 5)"
    )
    preview_parser.add_argument(
        "--workspace", "-w", type=str, help="Override workspace directory"
    )
    preview_parser.set_defaults(func=cmd_preview)

    # validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate a recipe file"
    )
    validate_parser.add_argument(
        "recipe", type=str, help="Path to recipe JSON file"
    )
    validate_parser.set_defaults(func=cmd_validate)

    # list-processors command
    list_parser = subparsers.add_parser(
        "list-processors", help="List available processors"
    )
    list_parser.set_defaults(func=cmd_list_processors)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
