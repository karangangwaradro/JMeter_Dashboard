"""
test_blazemeter_raw.py — Unit tests for BlazeMeter raw artifacts ingestion (kpi.jtl, error.jtl, and zip bundles).
"""

import tempfile
import unittest
import zipfile
from pathlib import Path

from app.domain.models.aggregate import AggregateResult
from app.domain.models.timeseries import TimeSeriesResult
from app.integrations.blazemeter.aggregate_parser import blazemeter_aggregate_parser
from app.integrations.blazemeter.error_parser import blazemeter_error_parser
from app.integrations.blazemeter.kpi_parser import blazemeter_kpi_parser
from app.integrations.blazemeter.timeseries_parser import blazemeter_timeseries_parser
from app.integrations.upload.file_source import file_result_source

SAMPLE_KPI_CSV = """timeStamp,elapsed,label,responseCode,responseMessage,threadName,success,bytes,grpThreads,allThreads,Latency,Hostname,Connect
1600000000000,200,TC01_T_01_Launch,200,,TG_01-ThreadStarter 1-1,true,500,1,5,180,host1,20
1600000001000,80,TC01_T_01_R_01_GET_Home,200,,TG_01-ThreadStarter 1-1,true,250,1,5,70,host1,10
1600000002000,120,TC01_T_01_R_02_GET_Assets,404,Not Found,TG_01-ThreadStarter 1-1,false,250,1,5,110,host1,10
1600000005000,600,TC01_T_02_Search,500,Server Error,TG_01-ThreadStarter 1-1,false,800,1,5,580,host1,20
1600000006000,600,TC01_T_02_R_01_POST_Query,500,Server Error,TG_01-ThreadStarter 1-1,false,800,1,5,580,host1,20
"""

SAMPLE_ERROR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<testResults version="1.2">
<httpSample t="120" lt="110" ts="1600000002000" s="false" lb="TC01_T_01_R_02_GET_Assets" rc="404" rm="" tn="TG_01-ThreadStarter 1-1">
  <responseData class="java.lang.String">&lt;!doctype html&gt;&lt;html&gt;&lt;head&gt;&lt;title&gt;HTTP Status 404 - Not Found&lt;/title&gt;&lt;/head&gt;&lt;body&gt;&lt;p&gt;&lt;b&gt;Message&lt;/b&gt; The requested resource [/assets/logo.png] is not available&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</responseData>
  <java.net.URL>https://petstore.octoperf.com/assets/logo.png</java.net.URL>
</httpSample>
<sample t="200" lt="180" ts="1600000000000" s="false" lb="TC01_T_01_Launch" rc="" rm="Number of samples in transaction : 2, number of failing samples : 1" tn="TG_01-ThreadStarter 1-1">
  <responseData class="java.lang.String">Non-TEXT response data</responseData>
</sample>
<httpSample t="600" lt="580" ts="1600000006000" s="false" lb="TC01_T_02_R_01_POST_Query" rc="500" rm="" tn="TG_01-ThreadStarter 1-1">
  <responseData class="java.lang.String">&lt;h1&gt;Stripes validation error report&lt;/h1&gt;&lt;p&gt;Source page resolution missing&lt;/p&gt;</responseData>
  <java.net.URL>https://petstore.octoperf.com/actions/Search.action</java.net.URL>
</httpSample>
</testResults>
"""


class TestBlazeMeterRawIngestion(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

        self.kpi_file = self.tmp_path / "kpi.jtl"
        self.kpi_file.write_text(SAMPLE_KPI_CSV, encoding="utf-8")

        self.error_file = self.tmp_path / "error.jtl"
        self.error_file.write_text(SAMPLE_ERROR_XML, encoding="utf-8")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_error_parser(self):
        errors = blazemeter_error_parser.parse_errors(self.error_file)
        self.assertEqual(len(errors), 2)

        # Verify 404 message extraction
        key_404 = next((k for k in errors if "404" in k), None)
        self.assertIsNotNone(key_404)
        self.assertIn("The requested resource [/assets/logo.png] is not available", errors[key_404].message)
        self.assertEqual(errors[key_404].count, 1)
        self.assertEqual(errors[key_404].occurrences[0].label, "TC01_T_01_R_02_GET_Assets")

        # Verify 500 stripes error extraction
        key_500 = next((k for k in errors if "500" in k), None)
        self.assertIsNotNone(key_500)
        self.assertIn("Stripes validation error", errors[key_500].message)
        self.assertEqual(errors[key_500].count, 1)

    def test_kpi_parser_aggregate(self):
        agg = blazemeter_kpi_parser.parse_kpi(
            self.kpi_file,
            test_id="test_bm_run",
            options={"error_jtl_path": str(self.error_file)},
        )

        self.assertIsInstance(agg, AggregateResult)
        self.assertEqual(agg.tool, "blazemeter")
        # 2 transactions: TC01_T_01_Launch and TC01_T_02_Search
        self.assertEqual(len(agg.transactions), 2)
        # 3 HTTP requests
        self.assertEqual(len(agg.http_requests), 3)
        # Total transactions executed = 2
        self.assertEqual(agg.total_requests, 2)
        # 1 failed transaction (TC01_T_02_Search failed)
        self.assertEqual(agg.failed_requests, 1)
        self.assertEqual(agg.error_rate, 50.0)

        # Verify thread group clean name
        self.assertIn("TG_01", agg.transactions_by_thread_group)

        # Verify errors breakdown populated from error.jtl
        self.assertEqual(len(agg.errors_breakdown), 2)

    def test_kpi_parser_timeseries(self):
        ts = blazemeter_kpi_parser.parse_timeseries(
            self.kpi_file,
            test_id="test_bm_run",
            bucket_seconds=10,
        )

        self.assertIsInstance(ts, TimeSeriesResult)
        self.assertEqual(ts.tool, "blazemeter")
        self.assertGreater(len(ts.bucket_labels), 0)
        self.assertEqual(len(ts.avg_response_time), len(ts.bucket_labels))
        self.assertEqual(max(ts.active_threads), 5)

    def test_aggregate_parser_dispatch(self):
        agg = blazemeter_aggregate_parser.parse_aggregate(
            self.tmp_path,  # Passing directory containing kpi.jtl
            test_id="test_dir_dispatch",
        )
        self.assertEqual(agg.tool, "blazemeter")
        self.assertEqual(len(agg.transactions), 2)

    def test_zip_bundle_upload(self):
        zip_path = self.tmp_path / "bundle.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(self.kpi_file, arcname="kpi.jtl")
            zf.write(self.error_file, arcname="error.jtl")

        opts = {}
        primary_path = file_result_source.fetch_data(str(zip_path), options=opts)
        self.assertTrue(primary_path.exists())
        self.assertEqual(primary_path.name, "kpi.jtl")
        self.assertIn("error_jtl_path", opts)
        self.assertTrue(Path(opts["error_jtl_path"]).exists())


if __name__ == "__main__":
    unittest.main()
