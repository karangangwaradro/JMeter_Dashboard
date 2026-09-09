"""
Unit tests for Server Metrics parsers (Azure, Prometheus, CSV).
"""

import unittest
from pathlib import Path
from app.server_metrics.azure.parser import azure_metrics_parser
from app.server_metrics.prometheus.parser import prometheus_metrics_parser
from app.server_metrics.csv.parser import csv_metrics_parser


class TestServerMetricsParsers(unittest.TestCase):

    def test_azure_metrics_parser(self):
        sample_azure = Path("Results/json/azure_20260820_130630.json")
        if not sample_azure.exists():
            self.skipTest("Sample azure file not found")

        srv = azure_metrics_parser.parse_server_metrics(sample_azure)
        self.assertEqual(srv.schema_version, "1.0")
        self.assertEqual(srv.provider, "azure_monitor")
        self.assertTrue(srv.configured)
        self.assertAlmostEqual(srv.infra_summary.avg_cpu, 60.73, places=1)
        self.assertAlmostEqual(srv.infra_summary.max_cpu, 91.4, places=1)
        self.assertEqual(len(srv.time_series["cpu"]), 6)
        self.assertTrue(len(srv.points) > 0)

    def test_prometheus_metrics_parser(self):
        mock_prometheus = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"__name__": "node_cpu_utilization", "instance": "prod-node-1"},
                        "values": [
                            [1690000000, "45.2"],
                            [1690000015, "55.8"],
                            [1690000030, "72.4"],
                        ]
                    },
                    {
                        "metric": {"__name__": "node_memory_utilization", "instance": "prod-node-1"},
                        "values": [
                            [1690000000, "65.0"],
                            [1690000015, "66.5"],
                            [1690000030, "68.0"],
                        ]
                    }
                ]
            }
        }
        srv = prometheus_metrics_parser.parse_server_metrics(mock_prometheus)
        self.assertEqual(srv.schema_version, "1.0")
        self.assertEqual(srv.provider, "prometheus")
        self.assertEqual(len(srv.time_series["cpu"]), 3)
        self.assertAlmostEqual(srv.infra_summary.avg_cpu, 57.8, places=1)
        self.assertAlmostEqual(srv.infra_summary.max_cpu, 72.4, places=1)

    def test_csv_metrics_parser(self):
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tf:
            tf.write("timestamp,cpu,memory,network_in,network_out,host\n")
            tf.write("2026-09-09T10:00:00Z,25.0,50.0,10.0,5.0,app-srv-1\n")
            tf.write("2026-09-09T10:01:00Z,35.0,52.0,15.0,8.0,app-srv-1\n")
            tf.write("2026-09-09T10:02:00Z,45.0,55.0,20.0,12.0,app-srv-1\n")
            tf_path = Path(tf.name)

        try:
            srv = csv_metrics_parser.parse_server_metrics(tf_path)
            self.assertEqual(srv.schema_version, "1.0")
            self.assertEqual(srv.provider, "csv")
            self.assertEqual(srv.infra_summary.avg_cpu, 35.0)
            self.assertEqual(srv.infra_summary.max_cpu, 45.0)
            self.assertEqual(len(srv.time_series["cpu"]), 3)
        finally:
            if tf_path.exists():
                tf_path.unlink()


if __name__ == "__main__":
    unittest.main()
