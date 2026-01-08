"""Processor registry for MiniDP."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from .errors import RegistryError

if TYPE_CHECKING:
    from .processors_base import BaseProcessor


class ProcessorRegistry:
    """
    Registry for processor classes.

    Supports two ways to resolve processor types:
    1. Registered names (e.g., "AddConstantFields")
    2. Import paths with dots (e.g., "mymodule.MyProcessor")

    Example:
        registry = ProcessorRegistry()
        registry.register("MyProcessor", MyProcessorClass)
        proc = registry.create("MyProcessor", param1="value")
    """

    def __init__(self) -> None:
        self._processors: dict[str, type[BaseProcessor]] = {}

    def register(self, name: str, cls: type[BaseProcessor]) -> None:
        """
        Register a processor class with a name.

        Args:
            name: The name to register the processor under.
            cls: The processor class.

        Raises:
            RegistryError: If the name is already registered.
        """
        if name in self._processors:
            raise RegistryError(
                f"Processor '{name}' is already registered. "
                f"Use a different name or unregister first."
            )
        self._processors[name] = cls

    def unregister(self, name: str) -> None:
        """
        Remove a processor from the registry.

        Args:
            name: The name of the processor to remove.
        """
        self._processors.pop(name, None)

    def get(self, processor_type: str) -> type[BaseProcessor]:
        """
        Get a processor class by name or import path.

        Args:
            processor_type: Either a registered name or a dotted import path
                  (e.g., "mypackage.processors.MyProcessor").

        Returns:
            The processor class.

        Raises:
            RegistryError: If the processor cannot be found.
        """
        # First check if it's in the registry
        if processor_type in self._processors:
            return self._processors[processor_type]

        # If it contains a dot, try to import it
        if "." in processor_type:
            return self._import_processor(processor_type)

        raise RegistryError(
            f"Processor '{processor_type}' not found in registry. "
            f"Available processors: {list(self._processors.keys())}"
        )

    def _import_processor(self, import_path: str) -> type[BaseProcessor]:
        """
        Import a processor class from a dotted path.

        Args:
            import_path: Full import path (e.g., "mypackage.MyProcessor").

        Returns:
            The imported processor class.

        Raises:
            RegistryError: If import fails.
        """
        try:
            module_path, class_name = import_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)

            # Import BaseProcessor here to avoid circular import at module level
            from .processors_base import BaseProcessor

            if not isinstance(cls, type) or not issubclass(cls, BaseProcessor):
                raise RegistryError(
                    f"'{import_path}' is not a BaseProcessor subclass"
                )
            return cls
        except ImportError as e:
            raise RegistryError(
                f"Failed to import processor '{import_path}': {e}"
            ) from e
        except AttributeError as e:
            raise RegistryError(
                f"Class not found in module '{import_path}': {e}"
            ) from e

    def create(self, processor_type: str, **kwargs: Any) -> BaseProcessor:
        """
        Create a processor instance by name.

        Args:
            processor_type: Processor name or import path.
            **kwargs: Arguments to pass to the processor constructor.

        Returns:
            A new processor instance.

        Raises:
            RegistryError: If the processor cannot be found or instantiated.
        """
        cls = self.get(processor_type)
        try:
            return cls(**kwargs)
        except TypeError as e:
            raise RegistryError(
                f"Failed to instantiate processor '{processor_type}': {e}"
            ) from e

    def list_processors(self) -> list[str]:
        """
        List all registered processor names.

        Returns:
            List of registered processor names.
        """
        return list(self._processors.keys())

    def __contains__(self, name: str) -> bool:
        """Check if a processor name is registered."""
        return name in self._processors


# Global default registry instance
_default_registry: ProcessorRegistry | None = None


def get_default_registry() -> ProcessorRegistry:
    """
    Get the default global processor registry.

    Returns:
        The default ProcessorRegistry instance.
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = ProcessorRegistry()
    return _default_registry


def register_processor(name: str):
    """
    Decorator to register a processor class with the default registry.

    Example:
        @register_processor("MyProcessor")
        class MyProcessor(BaseMapProcessor):
            ...
    """

    def decorator(cls: type[BaseProcessor]) -> type[BaseProcessor]:
        get_default_registry().register(name, cls)
        return cls

    return decorator
