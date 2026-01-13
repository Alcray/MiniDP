"""Custom processors for MiniDP.

This module provides a registry for user-defined custom processors.
Custom processors can be registered here and used in recipes by setting
use_custom_function=True when creating recipes.

To add a custom processor:
1. Create a class that inherits from BaseProcessor or BaseMapProcessor
2. Use @register_custom_processor("ProcessorName") decorator
3. Add an entry to custom_processors_registry.jsonl with metadata

Example:
    from minidp.custom_processors import register_custom_processor
    from minidp import BaseMapProcessor, DataEntry

    @register_custom_processor("MyCustomProcessor")
    class MyCustomProcessor(BaseMapProcessor):
        def __init__(self, my_param: str, **kwargs):
            super().__init__(**kwargs)
            self.my_param = my_param

        def process_record(self, record):
            # Custom processing logic
            return [DataEntry(data=record)]
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..errors import RegistryError

if TYPE_CHECKING:
    from ..processors_base import BaseProcessor


class CustomProcessorRegistry:
    """
    Registry for custom processor classes.
    
    This is separate from the main processor registry to distinguish
    between built-in and user-defined processors.
    """

    def __init__(self) -> None:
        self._processors: dict[str, type[BaseProcessor]] = {}

    def register(self, name: str, cls: type[BaseProcessor]) -> None:
        """
        Register a custom processor class with a name.

        Args:
            name: The name to register the processor under.
            cls: The processor class.

        Raises:
            RegistryError: If the name is already registered.
        """
        if name in self._processors:
            raise RegistryError(
                f"Custom processor '{name}' is already registered. "
                f"Use a different name or unregister first."
            )
        self._processors[name] = cls

    def unregister(self, name: str) -> None:
        """
        Remove a custom processor from the registry.

        Args:
            name: The name of the processor to remove.
        """
        self._processors.pop(name, None)

    def get(self, processor_type: str) -> type[BaseProcessor]:
        """
        Get a custom processor class by name.

        Args:
            processor_type: The registered name.

        Returns:
            The processor class.

        Raises:
            RegistryError: If the processor cannot be found.
        """
        if processor_type in self._processors:
            return self._processors[processor_type]

        raise RegistryError(
            f"Custom processor '{processor_type}' not found in registry. "
            f"Available custom processors: {list(self._processors.keys())}"
        )

    def create(self, processor_type: str, **kwargs: Any) -> BaseProcessor:
        """
        Create a custom processor instance by name.

        Args:
            processor_type: Processor name.
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
                f"Failed to instantiate custom processor '{processor_type}': {e}"
            ) from e

    def list_processors(self) -> list[str]:
        """
        List all registered custom processor names.

        Returns:
            List of registered custom processor names.
        """
        return list(self._processors.keys())

    def __contains__(self, name: str) -> bool:
        """Check if a custom processor name is registered."""
        return name in self._processors


# Global default custom registry instance
_default_custom_registry: CustomProcessorRegistry | None = None


def get_default_custom_registry() -> CustomProcessorRegistry:
    """
    Get the default global custom processor registry.

    Returns:
        The default CustomProcessorRegistry instance.
    """
    global _default_custom_registry
    if _default_custom_registry is None:
        _default_custom_registry = CustomProcessorRegistry()
    return _default_custom_registry


def register_custom_processor(name: str):
    """
    Decorator to register a custom processor class with the default custom registry.

    Example:
        @register_custom_processor("MyCustomProcessor")
        class MyCustomProcessor(BaseMapProcessor):
            ...
    """

    def decorator(cls: type[BaseProcessor]) -> type[BaseProcessor]:
        get_default_custom_registry().register(name, cls)
        return cls

    return decorator


# Auto-generated import
from .add_prefix_processor import AddPrefixProcessor

# Auto-generated import
from .text_uppercase_processor import TextUppercaseProcessor

__all__ = [
    "CustomProcessorRegistry",
    "get_default_custom_registry",
    "register_custom_processor",
    "AddPrefixProcessor",
    "TextUppercaseProcessor",
]
