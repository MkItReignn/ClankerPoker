"""Protocol for configuration loaders."""

from typing import Protocol, TypeVar

T_co = TypeVar("T_co", covariant=True)


class ConfigLoader(Protocol[T_co]):
    """Protocol that all config loaders should implement.

    This protocol ensures consistent interface across all configuration loaders,
    enabling type checking and making the contract explicit.
    """

    def load(self) -> T_co:
        """Load and return configuration object.

        Returns:
            Configuration object of type T_co.
        """
        ...
