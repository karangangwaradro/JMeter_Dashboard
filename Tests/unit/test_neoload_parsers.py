"""
Unit tests for NeoLoad parsers.
"""

import unittest
from app.integrations.neoload.aggregate_parser import neoload_aggregate_parser
from app.integrations.neoload.timeseries_parser import neoload_timeseries_parser


class TestNeoLoadParsers(unittest.TestCase):

    def setUp(self):
        self.mock_payload = {
            "statistics": {
                "totalRequestCount": 200,
                "totalErrorCount": 4,
                "totalRequestDurationAverage": 210.5,
                "totalDuration": 120.0,
            },
            "elements": [
                {
                    "name": "HomePage",
                    "count": 120,
                    "errorCount": 1,
                    "errorRate": 0.83,
                    "durationAverage": 180.0,
                    "durationMin": 40.0,
                    "durationMax": 800.0,
                    "durationP50": 170.0,
                    "durationP90": 260.0,
                    "durationP95": 320.0,
                    "durationP99": 500.0,
                },
                {
                    "name": "AddToCart",
                    "count": 80,
                    "errorCount": 3,
                    "errorRate": 3.75,
                    "durationAverage": 256.2,
                    "durationMin": 80.0,
                    "durationMax": 1100.0,
                    "durationP50": 240.0,
                    "durationP90": 380.0,
                    "durationP95": 490.0,
                    "durationP99": 750.0,
                },
            ],
            "points": [
                {"from": 1690000000, "durationAverage": 190.0, "durationP95": 300.0, "durationP99": 450.0, "throughput": 1.6, "errorCount": 0, "userCount": 5},
                {"from": 1690000010, "durationAverage": 230.0, "durationP95": 350.0, "durationP99": 520.0, "throughput": 1.7, "errorCount": 4, "userCount": 5},
            ]
        }

    def test_neoload_aggregate_parsing(self):
        agg = neoload_aggregate_parser.parse_aggregate(self.mock_payload, "nl_test_01")
        self.assertEqual(agg.schema_version, "1.0")
        self.assertEqual(agg.tool, "neoload")
        self.assertEqual(agg.total_requests, 200)
        self.assertEqual(agg.failed_requests, 4)
        self.assertEqual(agg.error_rate, 2.0)
        self.assertIn("HomePage", agg.transactions)
        self.assertIn("AddToCart", agg.transactions)
        self.assertEqual(agg.transactions["HomePage"].count, 120)

    def test_neoload_timeseries_parsing(self):
        ts = neoload_timeseries_parser.parse_timeseries(self.mock_payload, "nl_test_01")
        self.assertEqual(ts.schema_version, "1.0")
        self.assertEqual(ts.tool, "neoload")
        self.assertEqual(len(ts.bucket_labels), 2)
        self.assertEqual(ts.avg_response_time, [190.0, 230.0])
        self.assertEqual(ts.errors, [0, 4])


if __name__ == "__main__":
    unittest.main()
