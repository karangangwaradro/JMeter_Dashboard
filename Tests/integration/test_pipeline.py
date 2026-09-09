"""
Integration tests verifying complete end-to-end pipelines across JMeter, BlazeMeter, and NeoLoad.
Demonstrates that different input sources produce the same typed domain contracts and feed the SAME report generator.
"""

import unittest
from pathlib import Path
import tempfile
import json

from app.domain.models.test_run import ToolType, IngestionMethod
from app.integrations.jmeter.aggregate_parser import jmeter_aggregate_parser
from app.integrations.jmeter.timeseries_parser import jmeter_timeseries_parser
from app.integrations.blazemeter.aggregate_parser import blazemeter_aggregate_parser
from app.integrations.blazemeter.timeseries_parser import blazemeter_timeseries_parser
from app.integrations.neoload.aggregate_parser import neoload_aggregate_parser
from app.integrations.neoload.timeseries_parser import neoload_timeseries_parser
from app.services.reporting.generate_report import domain_report_generator
from app.services.orchestrator import orchestrator


class TestEndToEndPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.out_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_jmeter_pipeline(self):
        jtl_path = Path("Results/jtl/run_20260907_151915.jtl")
        if not jtl_path.exists():
            self.skipTest("Sample JTL not found")

        agg = jmeter_aggregate_parser.parse_aggregate(jtl_path, "pipeline_jmeter")
        ts = jmeter_timeseries_parser.parse_timeseries(jtl_path, "pipeline_jmeter")

        report_out = self.out_dir / "jmeter_report.html"
        res_path = domain_report_generator.generate(agg, ts, output_path=report_out, options={"test_name": "JMeter_Pipeline"})

        self.assertTrue(res_path.exists())
        self.assertGreater(res_path.stat().st_size, 50000)

    def test_blazemeter_pipeline(self):
        mock_bm = {
            "summary": {
                "result": [
                    {"label": "BM_Login", "samples": 150, "errors": 1, "avgResponseTime": 120.0, "95line": 250.0},
                    {"label": "BM_Search", "samples": 200, "errors": 0, "avgResponseTime": 95.0, "95line": 180.0},
                ],
                "duration": 60.0
            },
            "timeseries": {
                "result": [
                    {"avg_rt": 110.0, "p95": 200.0, "p99": 300.0, "tps": 5.8, "errors": 0, "users": 10},
                    {"avg_rt": 105.0, "p95": 190.0, "p99": 280.0, "tps": 5.8, "errors": 1, "users": 10},
                ]
            }
        }

        agg = blazemeter_aggregate_parser.parse_aggregate(mock_bm, "pipeline_bm")
        ts = blazemeter_timeseries_parser.parse_timeseries(mock_bm, "pipeline_bm")

        report_out = self.out_dir / "blazemeter_report.html"
        res_path = domain_report_generator.generate(agg, ts, output_path=report_out, options={"test_name": "BlazeMeter_Pipeline"})

        self.assertTrue(res_path.exists())
        self.assertGreater(res_path.stat().st_size, 50000)

    def test_neoload_pipeline(self):
        mock_nl = {
            "statistics": {
                "totalRequestCount": 350,
                "totalErrorCount": 2,
                "totalRequestDurationAverage": 135.0,
                "totalDuration": 60.0,
            },
            "elements": [
                {"name": "NL_Transaction_A", "count": 200, "errorCount": 1, "durationAverage": 110.0, "durationP95": 210.0},
                {"name": "NL_Transaction_B", "count": 150, "errorCount": 1, "durationAverage": 160.0, "durationP95": 290.0},
            ],
            "points": [
                {"from": 1690000000, "durationAverage": 130.0, "durationP95": 230.0, "throughput": 5.8, "errorCount": 1, "userCount": 8},
                {"from": 1690000010, "durationAverage": 140.0, "durationP95": 250.0, "throughput": 5.8, "errorCount": 1, "userCount": 8},
            ]
        }

        agg = neoload_aggregate_parser.parse_aggregate(mock_nl, "pipeline_nl")
        ts = neoload_timeseries_parser.parse_timeseries(mock_nl, "pipeline_nl")

        report_out = self.out_dir / "neoload_report.html"
        res_path = domain_report_generator.generate(agg, ts, output_path=report_out, options={"test_name": "NeoLoad_Pipeline"})

        self.assertTrue(res_path.exists())
        self.assertGreater(res_path.stat().st_size, 50000)

    def test_orchestrator_file_upload_ingest(self):
        jtl_path = Path("Results/jtl/run_20260907_151915.jtl")
        if not jtl_path.exists():
            self.skipTest("Sample JTL not found")

        res = orchestrator.ingest_and_process(
            tool=ToolType.JMETER,
            ingestion=IngestionMethod.FILE_UPLOAD,
            identifier=str(jtl_path),
            test_name="Orchestrator_Upload_Test",
            users=15,
            options={"ai_insights": {"source": "mock", "findings": [], "recommendations": []}},
        )

        self.assertTrue(res["success"])
        self.assertIn("report_url", res)
        self.assertTrue(Path(res["report_file"]).exists())
        self.assertEqual(res["summary"]["total"], 2976)

        # Verify HTML report contains compiled hierarchy: User Story -> Transaction -> Requests
        html_content = Path(res["report_file"]).read_text(encoding="utf-8")
        import re
        tg_matches = re.findall(r'<tr[^>]*tg-header-row', html_content)
        tx_matches = re.findall(r'data-type="transaction"', html_content)
        req_matches = re.findall(r'data-type="request"', html_content)
        self.assertEqual(len(tg_matches), 4)
        self.assertEqual(len(tx_matches), 48)
        self.assertEqual(len(req_matches), 192)


if __name__ == "__main__":
    unittest.main()
