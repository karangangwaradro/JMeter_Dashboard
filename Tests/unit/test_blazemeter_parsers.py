"""
Unit tests for BlazeMeter parsers.
"""

import unittest
from app.integrations.blazemeter.aggregate_parser import blazemeter_aggregate_parser
from app.integrations.blazemeter.timeseries_parser import blazemeter_timeseries_parser


class TestBlazeMeterParsers(unittest.TestCase):

    def setUp(self):
        self.mock_payload = {
            "master_id": "123456",
            "summary": {
                "result": [
                    {
                        "label": "Login",
                        "samples": 100,
                        "errors": 2,
                        "avgResponseTime": 150.0,
                        "minResponseTime": 45.0,
                        "maxResponseTime": 600.0,
                        "90line": 220.0,
                        "95line": 280.0,
                        "99line": 450.0,
                        "errorPercentage": 2.0,
                    },
                    {
                        "label": "Checkout",
                        "samples": 50,
                        "errors": 0,
                        "avgResponseTime": 320.0,
                        "minResponseTime": 120.0,
                        "maxResponseTime": 900.0,
                        "90line": 450.0,
                        "95line": 550.0,
                        "99line": 750.0,
                        "errorPercentage": 0.0,
                    },
                ],
                "duration": 60.0,
            },
            "timeseries": {
                "result": [
                    {"timestamp": 1690000000, "avg_rt": 140.0, "p95": 250.0, "p99": 350.0, "tps": 2.5, "errors": 0, "users": 10},
                    {"timestamp": 1690000010, "avg_rt": 180.0, "p95": 300.0, "p99": 420.0, "tps": 2.5, "errors": 2, "users": 10},
                ]
            }
        }

    def test_blazemeter_aggregate_parsing(self):
        agg = blazemeter_aggregate_parser.parse_aggregate(self.mock_payload, "bm_123456")
        self.assertEqual(agg.schema_version, "1.0")
        self.assertEqual(agg.tool, "blazemeter")
        self.assertEqual(agg.total_requests, 150)
        self.assertEqual(agg.failed_requests, 2)
        self.assertAlmostEqual(agg.error_rate, 1.33, places=2)
        self.assertIn("Login", agg.transactions)
        self.assertIn("Checkout", agg.transactions)
        self.assertEqual(agg.transactions["Login"].count, 100)

    def test_blazemeter_timeseries_parsing(self):
        ts = blazemeter_timeseries_parser.parse_timeseries(self.mock_payload, "bm_123456")
        self.assertEqual(ts.schema_version, "1.0")
        self.assertEqual(ts.tool, "blazemeter")
        self.assertEqual(len(ts.bucket_labels), 2)
        self.assertEqual(ts.avg_response_time, [140.0, 180.0])
        self.assertEqual(ts.errors, [0, 2])


if __name__ == "__main__":
    unittest.main()
