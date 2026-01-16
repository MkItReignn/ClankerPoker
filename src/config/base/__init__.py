"""Base classes and protocols for configuration loaders."""

from src.config.base.config_loader import BaseConfigLoader
from src.config.base.config_loader_protocol import ConfigLoader

__all__ = [
    "BaseConfigLoader",
    "ConfigLoader",
]
