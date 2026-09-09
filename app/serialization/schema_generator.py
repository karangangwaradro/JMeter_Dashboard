"""
schema_generator.py — Exports JSON schemas for domain models into schemas/.
"""

import json
from pathlib import Path
from app.core.constants import SCHEMAS_DIR
from app.domain.models.timeseries import TimeSeriesResult
from app.domain.models.aggregate import AggregateResult
from app.domain.models.server_metrics import ServerMetrics


def export_schemas():
    """Generates and writes json schema files for all primary domain contracts."""
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)

    ts_schema = TimeSeriesResult.model_json_schema()
    agg_schema = AggregateResult.model_json_schema()
    srv_schema = ServerMetrics.model_json_schema()

    (SCHEMAS_DIR / "timeseries.schema.json").write_text(json.dumps(ts_schema, indent=2), encoding="utf-8")
    (SCHEMAS_DIR / "aggregate.schema.json").write_text(json.dumps(agg_schema, indent=2), encoding="utf-8")
    (SCHEMAS_DIR / "server_metrics.schema.json").write_text(json.dumps(srv_schema, indent=2), encoding="utf-8")

    print(f"[Schemas] Generated schemas in {SCHEMAS_DIR}")


if __name__ == "__main__":
    export_schemas()
