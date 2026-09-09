"""
Unit tests for domain models and contracts.
"""

import unittest
from datetime import datetime, timezone
from app.domain.models.timeseries import TimeSeriesResult, LabelTimeSeries
from app.domain.models.aggregate import AggregateResult, TransactionMetric
from app.domain.models.server_metrics import ServerMetrics, InfraSummary
from app.domain.models.test_run import TestExecutionRequest, ToolType, IngestionMethod
from app.serialization.serializer import serializer


class TestDomainModels(unittest.TestCase):

    def test_timeseries_model_validation(self):
        now = datetime.now(timezone.utc)
        ts = TimeSeriesResult(
            schema_version="1.0",
            test_id="run_123",
            tool="jmeter",
            start_time=now,
            end_time=now,
            interval_seconds=10,
            bucket_labels=["10s", "20s"],
            avg_response_time=[100.5, 120.2],
            p95_response_time=[150.0, 180.0],
            p99_response_time=[200.0, 220.0],
            throughput=[10.0, 12.0],
            errors=[0, 1],
            active_threads=[5, 10],
            label_series={
                "Login": LabelTimeSeries(
                    label="Login",
                    avg_rt=[90.0, 110.0],
                    p95_rt=[120.0, 140.0],
                    p99_rt=[150.0, 170.0],
                    throughput=[5.0, 6.0],
                    errors=[0, 1],
                )
            }
        )
        self.assertEqual(ts.test_id, "run_123")
        self.assertEqual(ts.tool, "jmeter")
        self.assertEqual(len(ts.bucket_labels), 2)
        self.assertIn("Login", ts.label_series)

    def test_aggregate_model_validation(self):
        agg = AggregateResult(
            schema_version="1.0",
            test_id="run_123",
            tool="blazemeter",
            total_requests=500,
            successful_requests=490,
            failed_requests=10,
            error_rate=2.0,
            throughput=25.0,
            avg_response_time=215.4,
            min_response_time=50.0,
            max_response_time=1200.0,
            p50=180.0,
            p90=320.0,
            p95=450.0,
            p99=800.0,
            duration_seconds=20.0,
            start_epoch=1690000000,
            end_epoch=1690000020,
            transactions={
                "Search": TransactionMetric(
                    label="Search",
                    count=200,
                    errors=2,
                    error_rate=1.0,
                    avg_rt=190.0,
                    min_rt=60.0,
                    max_rt=800.0,
                    p50=170.0,
                    p90=280.0,
                    p95=390.0,
                    p99=600.0,
                )
            }
        )
        self.assertEqual(agg.test_id, "run_123")
        self.assertEqual(agg.total_requests, 500)
        self.assertEqual(agg.error_rate, 2.0)
        self.assertIn("Search", agg.transactions)

    def test_server_metrics_model_validation(self):
        srv = ServerMetrics(
            schema_version="1.0",
            provider="azure_monitor",
            configured=True,
            infra_summary=InfraSummary(
                avg_cpu=45.5,
                max_cpu=88.2,
                avg_memory=62.1,
                max_memory=75.0,
                avg_network_in_mbps=12.4,
                avg_network_out_mbps=8.1,
            ),
            time_series={
                "cpu": [30.0, 45.0, 88.2],
                "memory": [60.0, 62.0, 75.0],
            },
            timestamps=["2026-09-09T10:00:00Z", "2026-09-09T10:05:00Z", "2026-09-09T10:10:00Z"],
        )
        self.assertEqual(srv.provider, "azure_monitor")
        self.assertEqual(srv.infra_summary.avg_cpu, 45.5)
        self.assertEqual(len(srv.time_series["cpu"]), 3)

    def test_execution_request_validation(self):
        req = TestExecutionRequest(
            tool=ToolType.NEOLOAD,
            ingestion=IngestionMethod.DIRECT_API,
            test_identifier="neoload_test_01",
            users=25,
            duration="300",
        )
        self.assertEqual(req.tool, ToolType.NEOLOAD)
        self.assertEqual(req.ingestion, IngestionMethod.DIRECT_API)
        self.assertEqual(req.users, 25)


if __name__ == "__main__":
    unittest.main()
