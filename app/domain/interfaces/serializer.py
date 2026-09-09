"""
serializer.py — Abstract interface for domain model persistence and serialization.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class DomainSerializer(ABC):
    """Handles serialization and deserialization of versioned typed domain contracts."""

    @abstractmethod
    def serialize(self, model: BaseModel, target_path: Path) -> Path:
        """Serializes a validated domain model to a formatted, versioned JSON file."""
        pass

    @abstractmethod
    def deserialize(self, source_path: Path, model_cls: Type[T]) -> T:
        """Loads and validates a domain model from a JSON file."""
        pass
