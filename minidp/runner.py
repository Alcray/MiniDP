"""Pipeline runner for MiniDP."""

from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .errors import ProcessorError, RecipeValidationError
from .manifest import iter_jsonl
from .recipe import get_step_id, parse_steps_to_run, validate_recipe
from .registry import ProcessorRegistry, get_default_registry
from .types import Record


@dataclass
class RunContext:
    """
    Context passed to processors during execution.

    Attributes:
        run_id: Unique identifier for this pipeline run.
        workspace_dir: Base directory for outputs and temps.
        tmp_dir: Directory for temporary files.
        log_fn: Function to call for logging messages.
        env: Optional environment/configuration dict for user data.
    """

    run_id: str
    workspace_dir: str
    tmp_dir: str
    log_fn: Callable[[str], None] = field(default=print)
    env: dict[str, Any] = field(default_factory=dict)

    def log(self, message: str) -> None:
        """Log a message using the configured log function."""
        self.log_fn(f"[{self.run_id}] {message}")


class PipelineRunner:
    """
    Executes recipes by running processors in sequence.

    Handles:
    - Step selection via steps_to_run
    - Filtering by enabled flag
    - Auto-stitching of input/output manifests between steps
    - Temp file management
    """

    def __init__(
        self,
        registry: ProcessorRegistry | None = None,
        workspace_dir: str = "./runs",
        keep_temps: bool = False,
        log_fn: Callable[[str], None] | None = None,
    ) -> None:
        """
        Initialize the pipeline runner.

        Args:
            registry: Processor registry to use. Defaults to global registry.
            workspace_dir: Base directory for outputs. Can be overridden by recipe.
            keep_temps: Whether to keep temporary files after run.
            log_fn: Logging function. Defaults to print.
        """
        self.registry = registry or get_default_registry()
        self.workspace_dir = workspace_dir
        self.keep_temps = keep_temps
        self.log_fn = log_fn or print

    def run_recipe(self, recipe: dict[str, Any]) -> str:
        """
        Execute a recipe.

        Args:
            recipe: The recipe dictionary.

        Returns:
            Path to the final output manifest.

        Raises:
            RecipeValidationError: If the recipe is invalid.
            ProcessorError: If a processor fails.
        """
        # Validate recipe
        validate_recipe(recipe)

        # Set up paths
        workspace = recipe.get("workspace_dir", self.workspace_dir)
        workspace_path = Path(workspace)
        workspace_path.mkdir(parents=True, exist_ok=True)

        tmp_dir = workspace_path / ".tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # Get I/O manifests from recipe
        recipe_input = recipe.get("input_manifest")
        recipe_output = recipe.get("output_manifest")

        # Create run context
        run_id = str(uuid.uuid4())[:8]
        ctx = RunContext(
            run_id=run_id,
            workspace_dir=str(workspace_path),
            tmp_dir=str(tmp_dir),
            log_fn=self.log_fn,
            env=recipe.get("env", {}),
        )

        ctx.log(f"Starting pipeline: {recipe.get('name', 'unnamed')}")

        # Select and filter steps
        steps = recipe["steps"]
        steps_to_run = recipe.get("steps_to_run", "all")
        start_idx, end_idx = parse_steps_to_run(steps_to_run, len(steps))
        selected_steps = steps[start_idx:end_idx]

        # Filter by enabled
        enabled_steps = [
            (i + start_idx, step)
            for i, step in enumerate(selected_steps)
            if step.get("enabled", True)
        ]

        if not enabled_steps:
            ctx.log("No enabled steps to run")
            # Return input manifest or empty path
            return recipe_input or ""

        ctx.log(f"Running {len(enabled_steps)} step(s)")

        # Auto-stitch I/O paths
        stitched_steps = self._stitch_io(
            enabled_steps,
            recipe_input=recipe_input,
            recipe_output=recipe_output,
            tmp_dir=str(tmp_dir),
        )

        # Execute processors
        final_output = ""
        for original_idx, step, input_path, output_path in stitched_steps:
            step_id = get_step_id(step, original_idx)
            step_type = step["type"]
            params = step.get("params", {})

            ctx.log(f"Running step '{step_id}' ({step_type})")

            # Create processor instance
            proc = self.registry.create(
                step_type,
                input_manifest=input_path,
                output_manifest=output_path,
                name=step_id,
                **params,
            )

            # Execute
            try:
                final_output = proc.process(ctx)
            except Exception as e:
                raise ProcessorError(
                    f"Step '{step_id}' failed: {e}"
                ) from e

        # Clean up temps if requested
        if not self.keep_temps and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)

        ctx.log(f"Pipeline complete. Output: {final_output}")
        return final_output

    def _stitch_io(
        self,
        enabled_steps: list[tuple[int, dict[str, Any]]],
        recipe_input: str | None,
        recipe_output: str | None,
        tmp_dir: str,
    ) -> list[tuple[int, dict[str, Any], str | None, str]]:
        """
        Auto-stitch input/output manifest paths for steps.

        Rules:
        - If a step has explicit input_manifest, use it
        - Otherwise, use previous step's output (or recipe input for first step)
        - If a step has explicit output_manifest, use it
        - Otherwise, use temp file (except last step uses recipe output)

        Args:
            enabled_steps: List of (original_index, step_dict) tuples.
            recipe_input: Recipe-level input manifest path.
            recipe_output: Recipe-level output manifest path.
            tmp_dir: Directory for temp files.

        Returns:
            List of (original_index, step_dict, input_path, output_path) tuples.
        """
        result = []
        prev_output: str | None = recipe_input
        num_steps = len(enabled_steps)

        for step_num, (original_idx, step) in enumerate(enabled_steps):
            is_last = step_num == num_steps - 1

            # Determine input path
            explicit_input = step.get("input_manifest")
            input_path = explicit_input if explicit_input else prev_output

            # Determine output path
            explicit_output = step.get("output_manifest")
            if explicit_output:
                output_path = explicit_output
            elif is_last and recipe_output:
                output_path = recipe_output
            else:
                # Generate temp path
                step_id = get_step_id(step, original_idx)
                output_path = str(Path(tmp_dir) / f"{step_id}_output.jsonl")

            result.append((original_idx, step, input_path, output_path))
            prev_output = output_path

        return result

    def preview_recipe(
        self,
        recipe: dict[str, Any],
        n: int = 5,
    ) -> list[Record]:
        """
        Run a recipe and return the first N output records.

        This is useful for interactive recipe design and testing.

        Args:
            recipe: The recipe dictionary.
            n: Maximum number of records to return.

        Returns:
            List of up to N records from the output manifest.
        """
        # Run the full recipe
        output_path = self.run_recipe(recipe)

        if not output_path:
            return []

        # Read first N records
        records = []
        for record in iter_jsonl(output_path):
            records.append(record)
            if len(records) >= n:
                break

        return records


def run_recipe(recipe: dict[str, Any], **runner_kwargs: Any) -> str:
    """
    Convenience function to run a recipe with default settings.

    Args:
        recipe: The recipe dictionary.
        **runner_kwargs: Additional arguments for PipelineRunner.

    Returns:
        Path to the final output manifest.
    """
    runner = PipelineRunner(**runner_kwargs)
    return runner.run_recipe(recipe)
