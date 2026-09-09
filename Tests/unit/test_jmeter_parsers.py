"""
Unit tests for JMeter parsers against sample JTL data.
"""

import unittest
from pathlib import Path
from app.integrations.jmeter.aggregate_parser import jmeter_aggregate_parser
from app.integrations.jmeter.timeseries_parser import jmeter_timeseries_parser


class TestJMeterParsers(unittest.TestCase):

    def test_jmeter_parsers_with_actual_jtl(self):
        jtl_path = Path("Results/jtl/run_20260907_151915.jtl")
        if not jtl_path.exists():
            self.skipTest("Sample JTL not found")

        agg = jmeter_aggregate_parser.parse_aggregate(jtl_path, "run_test_01")
        ts = jmeter_timeseries_parser.parse_timeseries(jtl_path, "run_test_01")

        # Verify Aggregate Result contract
        self.assertEqual(agg.schema_version, "1.0")
        self.assertEqual(agg.tool, "jmeter")
        self.assertEqual(agg.total_requests, 2976)
        self.assertEqual(agg.failed_requests, 330)
        self.assertAlmostEqual(agg.throughput, 16.53, places=1)
        self.assertAlmostEqual(agg.avg_response_time, 298.95, places=1)
        self.assertEqual(len(agg.transactions), 48)
        self.assertEqual(len(agg.http_requests), 194)
        self.assertEqual(len(agg.all_labels), 242)
        self.assertEqual(agg.total_iterations, 15)
        self.assertEqual(len(agg.hierarchy_tree), 4)

        # Verify item_type classification
        for tx in agg.transactions.values():
            self.assertEqual(tx.item_type, "MAIN_TRANSACTION")
        for req in agg.http_requests.values():
            self.assertEqual(req.item_type, "HTTP_REQUEST")

        # Verify Time Series Result contract
        self.assertEqual(ts.schema_version, "1.0")
        self.assertEqual(ts.tool, "jmeter")
        self.assertEqual(len(ts.bucket_labels), len(ts.avg_response_time))
        self.assertEqual(len(ts.bucket_labels), len(ts.throughput))
        self.assertTrue(len(ts.label_series) > 0)


if __name__ == "__main__":
    unittest.main()
