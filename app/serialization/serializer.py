"""
serializer.py — Strongly typed JSON serialization and deserialization for domain contracts.
"""

import json
from pathlib import Path
from typing import Type, TypeVar
from pydantic import BaseModel

from app.core.exceptions import SerializationError, ValidationError
from app.domain.interfaces.serializer import DomainSerializer
from app.domain.models.timeseries import TimeSeriesResult
from app.domain.models.aggregate import AggregateResult
from app.domain.models.server_metrics import ServerMetrics

T = TypeVar("T", bound=BaseModel)


class JSONDomainSerializer(DomainSerializer):
    """Production-grade serializer enforcing schema validation on read/write."""

    def serialize(self, model: BaseModel, target_path: Path) -> Path:
        """Serializes a Pydantic domain model into a pretty-printed UTF-8 JSON file."""
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data_dict = model.model_dump(mode="json")
            json_text = json.dumps(data_dict, indent=2, ensure_ascii=False)
            target_path.write_text(json_text, encoding="utf-8")
            return target_path
        except Exception as e:
            raise SerializationError(
                f"Failed to serialize {model.__class__.__name__} to {target_path.name}: {e}",
                context={"target_path": str(target_path), "model": model.__class__.__name__}
            )

    def deserialize(self, source_path: Path, model_cls: Type[T]) -> T:
        """Loads and validates a domain model from a JSON file."""
        source_path = Path(source_path)
        if not source_path.exists():
            raise SerializationError(
                f"Cannot deserialize {model_cls.__name__}: File not found {source_path}",
                context={"source_path": str(source_path)}
            )
        try:
            content = source_path.read_text(encoding="utf-8")
            raw_dict = json.loads(content)
            return model_cls.model_validate(raw_dict)
        except Exception as e:
            raise ValidationError(
                f"Failed to validate and deserialize {model_cls.__name__} from {source_path.name}: {e}",
                context={"source_path": str(source_path), "model": model_cls.__name__}
            )


# Global singleton instance
serializer = JSONDomainSerializer()


def save_timeseries(result: TimeSeriesResult, target_path: Path) -> Path:
    return serializer.serialize(result, target_path)


def load_timeseries(source_path: Path) -> TimeSeriesResult:
    return serializer.deserialize(source_path, TimeSeriesResult)


def save_aggregate(result: AggregateResult, target_path: Path) -> Path:
    return serializer.serialize(result, target_path)


def load_aggregate(source_path: Path) -> AggregateResult:
    return serializer.deserialize(source_path, AggregateResult)


def save_server_metrics(result: ServerMetrics, target_path: Path) -> Path:
    return serializer.serialize(result, target_path)


def load_server_metrics(source_path: Path) -> ServerMetrics:
    return serializer.deserialize(source_path, ServerMetrics)
