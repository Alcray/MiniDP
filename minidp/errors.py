"""MiniDP custom exceptions."""


class MiniDPError(Exception):
    """Base exception for all MiniDP errors."""

    pass


class RecipeValidationError(MiniDPError):
    """Raised when a recipe fails validation."""

    pass


class ProcessorError(MiniDPError):
    """Raised when a processor encounters an error during execution."""

    pass


class RegistryError(MiniDPError):
    """Raised when there's an issue with the processor registry."""

    pass


class ManifestError(MiniDPError):
    """Raised when there's an issue reading/writing manifests."""

    pass


class ConfigurationError(MiniDPError):
    """Raised when there's a configuration issue (e.g., input == output manifest)."""

    pass
