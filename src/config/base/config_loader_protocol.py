"""Protocol for configuration loaders."""

from typing import Protocol, TypeVar

T = TypeVar("T")


class ConfigLoader(Protocol[T]):
    """Protocol that all config loaders should implement.

    This protocol ensures consistent interface across all configuration loaders,
    enabling type checking and making the contract explicit.
    """

    def load(self) -> T:
        """Load and return configuration object.

        Returns:
            Configuration object of type T.
        """
        ...
