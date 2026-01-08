"""Recipe parsing and validation for MiniDP."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .errors import RecipeValidationError

# Recipe schema version
RECIPE_VERSION = "0.1"

# Regex for slice-style steps_to_run (e.g., "2:", "1:4", ":3")
SLICE_PATTERN = re.compile(r"^(\d*):(\d*)$")


def validate_recipe(recipe: dict[str, Any]) -> None:
    """
    Validate a recipe dictionary.

    Args:
        recipe: The recipe dictionary to validate.

    Raises:
        RecipeValidationError: If validation fails.
    """
    # Check required top-level keys
    if "steps" not in recipe:
        raise RecipeValidationError("Recipe must have 'steps' key")

    steps = recipe["steps"]
    if not isinstance(steps, list):
        raise RecipeValidationError("'steps' must be a list")

    # Validate each step
    seen_ids = set()
    for i, step in enumerate(steps):
        _validate_step(step, i, seen_ids)

    # Validate steps_to_run if present
    steps_to_run = recipe.get("steps_to_run", "all")
    if not _is_valid_steps_to_run(steps_to_run):
        raise RecipeValidationError(
            f"Invalid 'steps_to_run': '{steps_to_run}'. "
            f"Must be 'all' or a slice like '2:', '1:4', ':3'"
        )


def _validate_step(
    step: dict[str, Any], index: int, seen_ids: set[str]
) -> None:
    """
    Validate a single step in the recipe.

    Args:
        step: The step dictionary.
        index: The step index (for error messages).
        seen_ids: Set of already-seen step IDs.

    Raises:
        RecipeValidationError: If the step is invalid.
    """
    if not isinstance(step, dict):
        raise RecipeValidationError(f"Step {index} must be a dictionary")

    # 'type' is required
    if "type" not in step:
        raise RecipeValidationError(f"Step {index} must have 'type' key")

    step_type = step["type"]
    if not isinstance(step_type, str) or not step_type:
        raise RecipeValidationError(
            f"Step {index} 'type' must be a non-empty string"
        )

    # 'params' must be a dict if present
    if "params" in step:
        if not isinstance(step["params"], dict):
            raise RecipeValidationError(
                f"Step {index} 'params' must be a dictionary"
            )

    # 'id' must be unique if present
    if "id" in step:
        step_id = step["id"]
        if not isinstance(step_id, str):
            raise RecipeValidationError(
                f"Step {index} 'id' must be a string"
            )
        if step_id in seen_ids:
            raise RecipeValidationError(
                f"Duplicate step id: '{step_id}'"
            )
        seen_ids.add(step_id)

    # 'enabled' must be bool if present
    if "enabled" in step and not isinstance(step["enabled"], bool):
        raise RecipeValidationError(
            f"Step {index} 'enabled' must be a boolean"
        )


def _is_valid_steps_to_run(value: Any) -> bool:
    """Check if steps_to_run value is valid."""
    if value == "all":
        return True
    if isinstance(value, str) and SLICE_PATTERN.match(value):
        return True
    return False


def parse_steps_to_run(value: str, num_steps: int) -> tuple[int, int]:
    """
    Parse steps_to_run into (start, end) indices.

    Args:
        value: Either "all" or a slice string like "2:", "1:4", ":3".
        num_steps: Total number of steps in the recipe.

    Returns:
        Tuple of (start_index, end_index) for slicing.
    """
    if value == "all":
        return 0, num_steps

    match = SLICE_PATTERN.match(value)
    if not match:
        raise RecipeValidationError(f"Invalid steps_to_run: '{value}'")

    start_str, end_str = match.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else num_steps

    return start, end


def load_recipe(path: str | Path) -> dict[str, Any]:
    """
    Load a recipe from a JSON file.

    Args:
        path: Path to the recipe JSON file.

    Returns:
        The recipe dictionary.

    Raises:
        RecipeValidationError: If the file cannot be read or parsed.
    """
    path = Path(path)

    if not path.exists():
        raise RecipeValidationError(f"Recipe file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            recipe = json.load(f)
    except json.JSONDecodeError as e:
        raise RecipeValidationError(f"Invalid JSON in recipe: {e}") from e
    except OSError as e:
        raise RecipeValidationError(f"Failed to read recipe: {e}") from e

    if not isinstance(recipe, dict):
        raise RecipeValidationError("Recipe must be a JSON object")

    validate_recipe(recipe)
    return recipe


def save_recipe(recipe: dict[str, Any], path: str | Path) -> None:
    """
    Save a recipe to a JSON file.

    Args:
        recipe: The recipe dictionary.
        path: Path to save to.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(recipe, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_step_id(step: dict[str, Any], index: int) -> str:
    """
    Get a unique identifier for a step.

    Args:
        step: The step dictionary.
        index: The step index.

    Returns:
        The step ID if present, otherwise "step_{index}".
    """
    return step.get("id", f"step_{index}")
