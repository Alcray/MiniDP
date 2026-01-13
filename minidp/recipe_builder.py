"""Recipe builder and processor discovery for MiniDP.

This module provides:
- get_processors(): Get information about all built-in processors
- get_custom_processors(): Get information about custom processors
- create_recipe(): Create and validate recipes with processor validation
- create_custom_processor(): Create a new custom processor file and register it
"""

from __future__ import annotations

import json
import re
import warnings
from pathlib import Path
from typing import Any

from .errors import RecipeValidationError, RegistryError
from .registry import get_default_registry
from .custom_processors import get_default_custom_registry


# Paths to registry files
_PROCESSORS_REGISTRY_PATH = Path(__file__).parent / "processors" / "processors_registry.jsonl"
_CUSTOM_PROCESSORS_REGISTRY_PATH = Path(__file__).parent / "custom_processors" / "custom_processors_registry.jsonl"
_CUSTOM_PROCESSORS_DIR = Path(__file__).parent / "custom_processors"


def _load_registry_file(path: Path) -> list[dict[str, Any]]:
    """
    Load processor metadata from a JSONL registry file.
    
    Args:
        path: Path to the JSONL registry file.
        
    Returns:
        List of processor metadata dictionaries.
    """
    if not path.exists():
        return []
    
    processors = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    processors.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return processors


def get_processors() -> list[dict[str, Any]]:
    """
    Get information about all registered built-in processors.
    
    Returns a list of dictionaries, each containing:
    - name: The processor name
    - description: What the processor does
    - base_class: The base class (BaseProcessor or BaseMapProcessor)
    - params: Dictionary of parameter definitions with types, requirements, and descriptions
    - example: Example usage in a recipe step
    
    Returns:
        List of processor information dictionaries.
    
    Example:
        >>> processors = get_processors()
        >>> for proc in processors:
        ...     print(f"{proc['name']}: {proc['description']}")
    """
    return _load_registry_file(_PROCESSORS_REGISTRY_PATH)


def get_custom_processors() -> list[dict[str, Any]]:
    """
    Get information about all registered custom processors.
    
    Returns a list of dictionaries, each containing:
    - name: The processor name
    - description: What the processor does
    - base_class: The base class (BaseProcessor or BaseMapProcessor)
    - params: Dictionary of parameter definitions with types, requirements, and descriptions
    - example: Example usage in a recipe step
    
    Returns:
        List of custom processor information dictionaries.
    
    Example:
        >>> custom_processors = get_custom_processors()
        >>> for proc in custom_processors:
        ...     print(f"{proc['name']}: {proc['description']}")
    """
    return _load_registry_file(_CUSTOM_PROCESSORS_REGISTRY_PATH)


def get_processor_names() -> list[str]:
    """
    Get names of all built-in processors.
    
    Returns:
        List of built-in processor names.
    """
    return [p["name"] for p in get_processors()]


def get_custom_processor_names() -> list[str]:
    """
    Get names of all custom processors.
    
    Returns:
        List of custom processor names.
    """
    return [p["name"] for p in get_custom_processors()]


def _get_processor_params(processor_name: str) -> dict[str, Any] | None:
    """
    Get parameter definitions for a processor from the registry.
    
    Args:
        processor_name: Name of the processor.
        
    Returns:
        Dictionary of parameter definitions or None if not found.
    """
    for proc in get_processors():
        if proc["name"] == processor_name:
            return proc.get("params", {})
    return None


def _get_custom_processor_params(processor_name: str) -> dict[str, Any] | None:
    """
    Get parameter definitions for a custom processor from the registry.
    
    Args:
        processor_name: Name of the custom processor.
        
    Returns:
        Dictionary of parameter definitions or None if not found.
    """
    for proc in get_custom_processors():
        if proc["name"] == processor_name:
            return proc.get("params", {})
    return None


def _validate_processor_params(
    processor_name: str,
    params: dict[str, Any],
    param_definitions: dict[str, Any],
    step_index: int,
) -> list[str]:
    """
    Validate processor parameters against their definitions.
    
    Args:
        processor_name: Name of the processor.
        params: The parameters provided in the step.
        param_definitions: Parameter definitions from registry.
        step_index: Index of the step (for error messages).
        
    Returns:
        List of validation error messages.
    """
    errors = []
    
    # Check for required parameters
    for param_name, param_def in param_definitions.items():
        if param_def.get("required", False) and param_name not in params:
            errors.append(
                f"Step {step_index} ({processor_name}): "
                f"Missing required parameter '{param_name}'"
            )
    
    # Check for unknown parameters (warn only, don't error)
    known_params = set(param_definitions.keys())
    # Common base class params that are always valid
    base_params = {
        "input_manifest", "output_manifest", "enabled", "name",
        "max_workers", "in_memory_chunksize"
    }
    known_params.update(base_params)
    
    for param_name in params:
        if param_name not in known_params:
            # This is just a warning, not an error - allows for flexibility
            warnings.warn(
                f"Step {step_index} ({processor_name}): "
                f"Unknown parameter '{param_name}'",
                UserWarning,
            )
    
    return errors


def _validate_step_processor(
    step: dict[str, Any],
    step_index: int,
    use_custom_function: bool,
) -> tuple[list[str], list[str]]:
    """
    Validate a step's processor type and parameters.
    
    Args:
        step: The step dictionary.
        step_index: Index of the step.
        use_custom_function: Whether to allow custom processors.
        
    Returns:
        Tuple of (errors, warnings) lists.
    """
    errors = []
    warning_messages = []
    
    processor_type = step.get("type")
    if not processor_type:
        errors.append(f"Step {step_index}: Missing 'type' field")
        return errors, warning_messages
    
    params = step.get("params", {})
    
    # Get registries
    default_registry = get_default_registry()
    custom_registry = get_default_custom_registry()
    
    # Check if processor is in built-in registry
    if processor_type in default_registry:
        # Validate parameters against registry metadata
        param_definitions = _get_processor_params(processor_type)
        if param_definitions is not None:
            param_errors = _validate_processor_params(
                processor_type, params, param_definitions, step_index
            )
            errors.extend(param_errors)
        return errors, warning_messages
    
    # Check if it's an import path (contains dot)
    if "." in processor_type:
        # Import paths bypass validation - assume user knows what they're doing
        return errors, warning_messages
    
    # Processor not found in built-in registry
    if use_custom_function:
        # Check if it's in custom registry
        if processor_type in custom_registry:
            # Valid custom processor - validate parameters
            param_definitions = _get_custom_processor_params(processor_type)
            if param_definitions is not None:
                param_errors = _validate_processor_params(
                    processor_type, params, param_definitions, step_index
                )
                errors.extend(param_errors)
            return errors, warning_messages
        
        # Check if it's in the custom processors registry file (but not loaded)
        custom_processor_names = get_custom_processor_names()
        if processor_type in custom_processor_names:
            warning_messages.append(
                f"Step {step_index}: Custom processor '{processor_type}' found "
                f"in registry but not loaded. Make sure to import it."
            )
            # Validate parameters from registry file
            param_definitions = _get_custom_processor_params(processor_type)
            if param_definitions is not None:
                param_errors = _validate_processor_params(
                    processor_type, params, param_definitions, step_index
                )
                errors.extend(param_errors)
            return errors, warning_messages
        
        # Not in custom registry either - this is an error
        errors.append(
            f"Step {step_index}: Processor '{processor_type}' not found in "
            f"built-in registry or custom processor registry. "
            f"Available built-in processors: {default_registry.list_processors()}. "
            f"Available custom processors: {custom_registry.list_processors()}"
        )
    else:
        # use_custom_function is False - error for unknown processor
        errors.append(
            f"Step {step_index}: Unknown processor '{processor_type}'. "
            f"Available processors: {default_registry.list_processors()}. "
            f"Set use_custom_function=True to use custom processors."
        )
    
    return errors, warning_messages


def create_recipe(
    steps: list[dict[str, Any]],
    use_custom_function: bool = False,
    name: str | None = None,
    version: str = "0.1",
    workspace_dir: str | None = None,
    input_manifest: str | None = None,
    output_manifest: str | None = None,
    steps_to_run: str = "all",
) -> dict[str, Any]:
    """
    Create and validate a recipe from processor steps.
    
    This function validates that all processors exist and have valid arguments
    before creating the recipe. If use_custom_function is True, it will also
    check the custom processor registry and emit warnings instead of errors
    for processors found there.
    
    Args:
        steps: List of step dictionaries, each containing:
            - type: The processor type name (required)
            - id: Optional unique identifier for the step
            - params: Optional dictionary of processor parameters
            - enabled: Optional boolean to enable/disable the step
        use_custom_function: If True, allows processors from the custom
            processor registry and emits warnings instead of errors for them.
            Default is False.
        name: Optional name for the pipeline.
        version: Recipe version. Default is "0.1".
        workspace_dir: Optional workspace directory path.
        input_manifest: Optional input manifest path.
        output_manifest: Optional output manifest path.
        steps_to_run: Which steps to run. Default is "all".
            Can be "all" or a slice like "2:", "1:4", ":3".
    
    Returns:
        The validated recipe dictionary.
    
    Raises:
        RecipeValidationError: If validation fails (invalid processor types,
            missing required parameters, etc.).
    
    Example:
        >>> recipe = create_recipe(
        ...     steps=[
        ...         {"id": "add_meta", "type": "AddConstantFields", 
        ...          "params": {"fields": {"source": "web"}}},
        ...         {"id": "filter", "type": "FilterByField",
        ...          "params": {"field": "lang", "values": ["en"]}}
        ...     ],
        ...     name="my_pipeline",
        ...     workspace_dir="./runs/my_pipeline"
        ... )
        
        >>> # With custom processors
        >>> recipe = create_recipe(
        ...     steps=[
        ...         {"type": "MyCustomProcessor", "params": {"custom_arg": "value"}}
        ...     ],
        ...     use_custom_function=True
        ... )
    """
    if not isinstance(steps, list):
        raise RecipeValidationError("'steps' must be a list")
    
    if not steps:
        raise RecipeValidationError("'steps' cannot be empty")
    
    all_errors = []
    all_warnings = []
    seen_ids = set()
    
    # Validate each step
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            all_errors.append(f"Step {i}: Must be a dictionary")
            continue
        
        # Check for duplicate IDs
        if "id" in step:
            step_id = step["id"]
            if not isinstance(step_id, str):
                all_errors.append(f"Step {i}: 'id' must be a string")
            elif step_id in seen_ids:
                all_errors.append(f"Step {i}: Duplicate step id '{step_id}'")
            else:
                seen_ids.add(step_id)
        
        # Validate 'enabled' field if present
        if "enabled" in step and not isinstance(step["enabled"], bool):
            all_errors.append(f"Step {i}: 'enabled' must be a boolean")
        
        # Validate 'params' field if present
        if "params" in step and not isinstance(step["params"], dict):
            all_errors.append(f"Step {i}: 'params' must be a dictionary")
            continue
        
        # Validate processor type and parameters
        step_errors, step_warnings = _validate_step_processor(
            step, i, use_custom_function
        )
        all_errors.extend(step_errors)
        all_warnings.extend(step_warnings)
    
    # Emit warnings
    for warning_msg in all_warnings:
        warnings.warn(warning_msg, UserWarning)
    
    # Raise error if validation failed
    if all_errors:
        error_msg = "Recipe validation failed:\n" + "\n".join(f"  - {e}" for e in all_errors)
        raise RecipeValidationError(error_msg)
    
    # Build the recipe
    recipe: dict[str, Any] = {
        "version": version,
        "steps": steps,
    }
    
    if name is not None:
        recipe["name"] = name
    
    if workspace_dir is not None:
        recipe["workspace_dir"] = workspace_dir
    
    if input_manifest is not None:
        recipe["input_manifest"] = input_manifest
    
    if output_manifest is not None:
        recipe["output_manifest"] = output_manifest
    
    if steps_to_run != "all":
        recipe["steps_to_run"] = steps_to_run
    
    return recipe


def add_custom_processor_to_registry(
    name: str,
    description: str,
    params: dict[str, dict[str, Any]],
    base_class: str = "BaseMapProcessor",
    example: dict[str, Any] | None = None,
) -> None:
    """
    Add a custom processor entry to the custom processors registry file.
    
    This allows you to document custom processors for discovery via
    get_custom_processors() and enables validation in create_recipe().
    
    Args:
        name: The processor name (must match the registered class name).
        description: Description of what the processor does.
        params: Dictionary of parameter definitions. Each parameter should have:
            - type: String describing the expected type
            - required: Boolean indicating if required
            - description: Description of the parameter
            - default: Optional default value
        base_class: The base class name ("BaseProcessor" or "BaseMapProcessor").
        example: Optional example usage dictionary.
    
    Example:
        >>> add_custom_processor_to_registry(
        ...     name="MyCustomProcessor",
        ...     description="Processes records in a custom way.",
        ...     params={
        ...         "custom_param": {
        ...             "type": "str",
        ...             "required": True,
        ...             "description": "A custom parameter"
        ...         }
        ...     },
        ...     example={"type": "MyCustomProcessor", "params": {"custom_param": "value"}}
        ... )
    """
    entry = {
        "name": name,
        "description": description,
        "base_class": base_class,
        "params": params,
    }
    
    if example is not None:
        entry["example"] = example
    
    # Append to the registry file
    with open(_CUSTOM_PROCESSORS_REGISTRY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _is_valid_python_identifier(name: str) -> bool:
    """Check if a string is a valid Python identifier."""
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name))


def _generate_processor_code(
    name: str,
    description: str,
    params: dict[str, dict[str, Any]],
    process_record_body: str,
    base_class: str = "BaseMapProcessor",
    imports: list[str] | None = None,
) -> str:
    """
    Generate Python code for a custom processor class.
    
    Args:
        name: The processor class name.
        description: Description for the docstring.
        params: Parameter definitions.
        process_record_body: The body of the process_record method.
        base_class: Base class name.
        imports: Additional import statements.
        
    Returns:
        Generated Python code as a string.
    """
    # Build imports section
    import_lines = [
        '"""Auto-generated custom processor."""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "",
        "from minidp import BaseMapProcessor, BaseProcessor, DataEntry, Record",
        "from minidp.custom_processors import get_default_custom_registry",
    ]
    
    if imports:
        import_lines.append("")
        import_lines.extend(imports)
    
    # Build __init__ parameters
    init_params = ["self"]
    init_assignments = []
    param_docs = []
    
    for param_name, param_def in params.items():
        param_type = param_def.get("type", "Any")
        required = param_def.get("required", True)
        default = param_def.get("default")
        param_desc = param_def.get("description", f"Parameter {param_name}")
        
        if required:
            init_params.append(f"{param_name}: {param_type}")
        else:
            default_repr = repr(default) if default is not None else "None"
            init_params.append(f"{param_name}: {param_type} = {default_repr}")
        
        init_assignments.append(f"        self.{param_name} = {param_name}")
        param_docs.append(f"        {param_name}: {param_desc}")
    
    init_params.append("**kwargs: Any")
    
    # Build class code
    code_lines = import_lines + [
        "",
        "",
        f"class {name}({base_class}):",
        f'    """',
        f"    {description}",
        "",
        "    Params:",
    ]
    code_lines.extend(param_docs)
    code_lines.extend([
        '    """',
        "",
        "    def __init__(",
    ])
    # Add each parameter on its own line
    for i, param in enumerate(init_params):
        if i < len(init_params) - 1:
            code_lines.append(f"        {param},")
        else:
            code_lines.append(f"        {param},")
    code_lines.extend([
        "    ) -> None:",
        f'        """Initialize {name}."""',
        "        super().__init__(**kwargs)",
    ])
    code_lines.extend(init_assignments)
    
    # Add process_record method
    if base_class == "BaseMapProcessor":
        code_lines.extend([
            "",
            "    def process_record(self, record: Record) -> list[DataEntry]:",
            '        """Process a single record."""',
        ])
        # Indent the process_record_body
        for line in process_record_body.strip().split("\n"):
            code_lines.append(f"        {line}" if line.strip() else "")
    else:
        code_lines.extend([
            "",
            "    def process(self, ctx) -> str:",
            '        """Execute the processor."""',
        ])
        for line in process_record_body.strip().split("\n"):
            code_lines.append(f"        {line}" if line.strip() else "")
    
    # Add registration at module level
    code_lines.extend([
        "",
        "",
        "# Register the processor",
        f'get_default_custom_registry().register("{name}", {name})',
        "",
    ])
    
    return "\n".join(code_lines)


def _convert_name_to_filename(name: str) -> str:
    """Convert a CamelCase class name to snake_case filename."""
    # Insert underscore before uppercase letters and convert to lowercase
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def create_custom_processor(
    name: str,
    description: str,
    params: dict[str, dict[str, Any]],
    process_record_body: str,
    base_class: str = "BaseMapProcessor",
    imports: list[str] | None = None,
    example: dict[str, Any] | None = None,
    overwrite: bool = False,
) -> str:
    """
    Create a new custom processor file and register it.
    
    This function:
    1. Validates the processor name and parameters
    2. Generates a Python file with the processor class
    3. Adds the processor to the custom_processors_registry.jsonl
    4. Updates the custom_processors/__init__.py to import the new processor
    
    Args:
        name: The processor class name (must be a valid Python identifier,
            typically CamelCase like "MyCustomProcessor").
        description: Description of what the processor does.
        params: Dictionary of parameter definitions. Each parameter should have:
            - type: String describing the expected type (e.g., "str", "int", "list[str]")
            - required: Boolean indicating if required (default True)
            - description: Description of the parameter
            - default: Default value (only for non-required params)
        process_record_body: The Python code for the process_record method body.
            For BaseMapProcessor, this should return a list[DataEntry].
            For BaseProcessor, this should be the process() method body.
            The code will be indented appropriately.
        base_class: Either "BaseMapProcessor" (default) or "BaseProcessor".
        imports: Optional list of additional import statements needed by your code.
        example: Optional example usage dictionary for documentation.
        overwrite: If True, overwrite existing processor file. Default False.
    
    Returns:
        Path to the created processor file.
    
    Raises:
        RecipeValidationError: If validation fails (invalid name, file exists, etc.).
    
    Example:
        >>> # Create a simple processor that adds a prefix to a field
        >>> filepath = create_custom_processor(
        ...     name="AddPrefixProcessor",
        ...     description="Add a prefix to a specified field.",
        ...     params={
        ...         "field": {
        ...             "type": "str",
        ...             "required": True,
        ...             "description": "Field name to modify"
        ...         },
        ...         "prefix": {
        ...             "type": "str",
        ...             "required": True,
        ...             "description": "Prefix to add"
        ...         }
        ...     },
        ...     process_record_body='''
        ... if self.field in record:
        ...     record[self.field] = self.prefix + str(record[self.field])
        ... return [DataEntry(data=record)]
        ... ''',
        ...     example={"type": "AddPrefixProcessor", "params": {"field": "name", "prefix": "Mr. "}}
        ... )
        
        >>> # Create a processor with optional params and custom imports
        >>> filepath = create_custom_processor(
        ...     name="RegexFilterProcessor",
        ...     description="Filter records based on regex pattern.",
        ...     params={
        ...         "field": {"type": "str", "required": True, "description": "Field to match"},
        ...         "pattern": {"type": "str", "required": True, "description": "Regex pattern"},
        ...         "invert": {"type": "bool", "required": False, "default": False, "description": "Invert match"}
        ...     },
        ...     process_record_body='''
        ... import re
        ... value = str(record.get(self.field, ""))
        ... matches = bool(re.search(self.pattern, value))
        ... if self.invert:
        ...     matches = not matches
        ... return [DataEntry(data=record)] if matches else []
        ... ''',
        ...     imports=["import re"]
        ... )
    """
    # Validate processor name
    if not _is_valid_python_identifier(name):
        raise RecipeValidationError(
            f"Invalid processor name '{name}'. Must be a valid Python identifier "
            "(letters, numbers, underscores, cannot start with a number)."
        )
    
    if not name[0].isupper():
        raise RecipeValidationError(
            f"Processor name '{name}' should start with an uppercase letter (CamelCase)."
        )
    
    # Validate base_class
    if base_class not in ("BaseMapProcessor", "BaseProcessor"):
        raise RecipeValidationError(
            f"Invalid base_class '{base_class}'. Must be 'BaseMapProcessor' or 'BaseProcessor'."
        )
    
    # Validate params
    if not isinstance(params, dict):
        raise RecipeValidationError("'params' must be a dictionary")
    
    for param_name, param_def in params.items():
        if not _is_valid_python_identifier(param_name):
            raise RecipeValidationError(
                f"Invalid parameter name '{param_name}'. Must be a valid Python identifier."
            )
        if not isinstance(param_def, dict):
            raise RecipeValidationError(
                f"Parameter '{param_name}' definition must be a dictionary."
            )
    
    # Check if processor already exists in registry
    existing_names = get_custom_processor_names()
    if name in existing_names and not overwrite:
        raise RecipeValidationError(
            f"Custom processor '{name}' already exists in registry. "
            "Set overwrite=True to replace it."
        )
    
    # Generate filename and path
    filename = _convert_name_to_filename(name) + ".py"
    filepath = _CUSTOM_PROCESSORS_DIR / filename
    
    # Check if file already exists
    if filepath.exists() and not overwrite:
        raise RecipeValidationError(
            f"File '{filepath}' already exists. Set overwrite=True to replace it."
        )
    
    # Generate processor code
    code = _generate_processor_code(
        name=name,
        description=description,
        params=params,
        process_record_body=process_record_body,
        base_class=base_class,
        imports=imports,
    )
    
    # Write processor file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    
    # Add to registry (if not already there or overwriting)
    if name not in existing_names:
        add_custom_processor_to_registry(
            name=name,
            description=description,
            params=params,
            base_class=base_class,
            example=example,
        )
    elif overwrite:
        # Remove old entry and add new one
        _remove_from_registry(name)
        add_custom_processor_to_registry(
            name=name,
            description=description,
            params=params,
            base_class=base_class,
            example=example,
        )
    
    # Update custom_processors/__init__.py to include import
    _update_custom_processors_init(name, filename)
    
    return str(filepath)


def _remove_from_registry(name: str) -> None:
    """Remove a processor entry from the registry file."""
    if not _CUSTOM_PROCESSORS_REGISTRY_PATH.exists():
        return
    
    lines = []
    with open(_CUSTOM_PROCESSORS_REGISTRY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line_stripped = line.strip()
            if line_stripped:
                try:
                    entry = json.loads(line_stripped)
                    if entry.get("name") != name:
                        lines.append(line)
                except json.JSONDecodeError:
                    lines.append(line)
    
    with open(_CUSTOM_PROCESSORS_REGISTRY_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _update_custom_processors_init(name: str, filename: str) -> None:
    """Update custom_processors/__init__.py to import the new processor."""
    init_path = _CUSTOM_PROCESSORS_DIR / "__init__.py"
    
    # Read current content
    with open(init_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Module name (without .py)
    module_name = filename[:-3]
    
    # Check if import already exists
    import_line = f"from .{module_name} import {name}"
    if import_line in content:
        return
    
    # Find the __all__ line and add import before it
    if "__all__" in content:
        # Add import just before __all__
        content = content.replace(
            "__all__",
            f"# Auto-generated import\n{import_line}\n\n__all__"
        )
    else:
        # Append at the end
        content += f"\n# Auto-generated import\n{import_line}\n"
    
    # Update __all__ if it exists
    all_match = re.search(r"__all__\s*=\s*\[([^\]]*)\]", content, re.DOTALL)
    if all_match:
        current_all = all_match.group(1)
        if f'"{name}"' not in current_all and f"'{name}'" not in current_all:
            # Add to __all__
            new_all = current_all.rstrip()
            if new_all and not new_all.rstrip().endswith(","):
                new_all += ","
            new_all += f'\n    "{name}",'
            content = content[:all_match.start(1)] + new_all + "\n" + content[all_match.end(1):]
    
    # Write updated content
    with open(init_path, "w", encoding="utf-8") as f:
        f.write(content)


__all__ = [
    "get_processors",
    "get_custom_processors",
    "get_processor_names",
    "get_custom_processor_names",
    "create_recipe",
    "create_custom_processor",
    "add_custom_processor_to_registry",
]
