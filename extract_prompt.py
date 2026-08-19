import json
import sys
sys.path.insert(0, r"D:\BlazemeterMCPZIP\JmeterAI")

from pathlib import Path
from python_files.ai_insights import _generate_gemini_insights

results_dir = Path(r"D:\BlazemeterMCPZIP\JmeterAI\Results")
json_dir = results_dir / "json"

latest = json_dir / "run_20260814_110019_result.json"
if not latest.exists():
    latest = results_dir / "run_20260814_110019_result.json"

az_file = json_dir / "azure_20260814_110019.json"
if not az_file.exists():
    az_file = results_dir / "azure_20260814_110019.json"

with open(latest, "r", encoding="utf-8") as f:
    parsed = json.load(f)

azure_data = {}
if az_file.exists():
    with open(az_file, "r", encoding="utf-8") as f:
        azure_data = json.load(f)

# Mock the urllib request to capture the payload
import urllib.request
class MockRequest:
    def __init__(self, url, data=None, headers=None, method=None):
        self.data = data

def mock_urlopen(req):
    payload = json.loads(req.data.decode('utf-8'))
    prompt_text = payload['contents'][0]['parts'][0]['text']
    with open(results_dir / "captured_prompt.txt", "w", encoding="utf-8") as out:
        out.write(prompt_text)
    raise Exception("Stop execution")

urllib.request.Request = MockRequest
urllib.request.urlopen = mock_urlopen

try:
    _generate_gemini_insights(
        api_key="fake",
        test_name=parsed.get("jmx_name", "Scenario"),
        summary=parsed.get("summary", {}),
        labels=parsed.get("labels", {}),
        time_series=parsed.get("time_series", {}),
        infra=azure_data.get("infra_summary", {}),
        correlation=parsed.get("correlation", {})
    )
except Exception as e:
    pass
