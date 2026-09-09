"""
test_jmeter_runner.py — Unit tests for JMeterRunner execution lifecycle and status querying.
Verifies thread-safety, RLock re-entrancy, and status reporting without deadlocks.
"""
import unittest
from unittest.mock import patch, MagicMock
from app.integrations.jmeter.runner import JMeterRunner
from app.domain.models.test_run import TestExecutionRequest, ToolType, IngestionMethod


class TestJMeterRunner(unittest.TestCase):

    def setUp(self):
        self.runner = JMeterRunner()

    def test_get_status_idle(self):
        st = self.runner.get_status()
        self.assertEqual(st.status, "idle")
        self.assertFalse(st.active)
        self.assertFalse(st.running)
        self.assertEqual(st.tool, ToolType.JMETER)

    def test_lock_reentrancy(self):
        """Ensure acquire / get_status can be called recursively without deadlocking."""
        with self.runner._lock:
            st = self.runner.get_status()
            self.assertIsNotNone(st)
            self.assertEqual(st.status, "idle")

    @patch.object(JMeterRunner, "check_jmeter")
    def test_start_test_launches_without_deadlock(self, mock_check):
        mock_check.return_value = {"available": True, "bin": "jmeter"}
        req = TestExecutionRequest(
            tool=ToolType.JMETER,
            ingestion=IngestionMethod.LOCAL,
            test_identifier="JPetStore_MultiUserStories.jmx",
            users=1
        )
        with patch("subprocess.Popen") as mock_popen, \
             patch("threading.Thread") as mock_thread:
            mock_proc = MagicMock()
            mock_proc.stdout.readline.return_value = ""
            mock_proc.wait.return_value = 0
            mock_popen.return_value = mock_proc

            st = self.runner.start_test(req)
            self.assertTrue(st.active)
            self.assertTrue(st.running)
            self.assertEqual(st.status, "running")

    def test_stop_test_idle(self):
        stopped = self.runner.stop_test()
        self.assertTrue(stopped)
        st = self.runner.get_status()
        self.assertFalse(st.active)


if __name__ == "__main__":
    unittest.main()
