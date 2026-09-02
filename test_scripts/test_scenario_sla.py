#!/usr/bin/env python3
"""
test_scenario_sla.py — Unit test for Load-Scenario-Based SLA System and Nearest-Neighbor Matching.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
_ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(_ROOT_DIR))

from python_files.sla_manager import (
    load_sla_targets,
    load_sla_scenarios_and_targets,
    save_sla_targets,
    match_nearest_scenario,
    get_matched_scenario_info
)


class TestScenarioSLA(unittest.TestCase):

    def setUp(self):
        self.test_jmx = "Test_Scenario_Demo.jmx"
        self.test_csv = _ROOT_DIR / "Tests" / "Test_Scenario_Demo_sla.csv"
        if self.test_csv.exists():
            self.test_csv.unlink()

    def tearDown(self):
        if self.test_csv.exists():
            self.test_csv.unlink()

    def test_nearest_scenario_matching_logic(self):
        scenarios = [
            {"id": "sc_normal_50", "name": "Normal Load", "users": 50},
            {"id": "sc_peak_200", "name": "Peak Load", "users": 200},
            {"id": "sc_spike_500", "name": "Spike Load", "users": 500}
        ]

        # 40 users should match Normal Load (50)
        matched, diff = match_nearest_scenario(scenarios, 40)
        self.assertEqual(matched["name"], "Normal Load")
        self.assertEqual(diff, 10.0)

        # 180 users should match Peak Load (200)
        matched, diff = match_nearest_scenario(scenarios, 180)
        self.assertEqual(matched["name"], "Peak Load")
        self.assertEqual(diff, 20.0)

        # 400 users should match Spike Load (500)
        matched, diff = match_nearest_scenario(scenarios, 400)
        self.assertEqual(matched["name"], "Spike Load")
        self.assertEqual(diff, 100.0)

        # 50 users exact match
        matched, diff = match_nearest_scenario(scenarios, 50)
        self.assertEqual(matched["name"], "Normal Load")
        self.assertEqual(diff, 0.0)

    def test_save_and_load_multi_scenario_sla(self):
        scenarios = [
            {"id": "sc_normal_50", "name": "Normal Load", "users": 50},
            {"id": "sc_peak_200", "name": "Peak Load", "users": 200}
        ]

        slas = [
            {
                "label": "default",
                "rt": 500,
                "err": 1.0,
                "is_critical": 0,
                "scenarios": {
                    "sc_normal_50": {"rt": 300, "err": 0.5},
                    "sc_peak_200": {"rt": 600, "err": 1.5}
                }
            },
            {
                "label": "TC01_Launch",
                "rt": 250,
                "err": 1.0,
                "is_critical": 1,
                "scenarios": {
                    "sc_normal_50": {"rt": 150, "err": 0.2},
                    "sc_peak_200": {"rt": 350, "err": 1.0}
                }
            },
            {
                "label": "TC02_Checkout",
                "rt": 800,
                "err": 2.0,
                "is_critical": 1,
                "scenarios": {
                    "sc_normal_50": {"rt": 500, "err": 1.0},
                    "sc_peak_200": {"rt": 1200, "err": 3.0}
                }
            }
        ]

        saved_path = save_sla_targets(slas, self.test_jmx, scenarios=scenarios)
        self.assertTrue(Path(saved_path).exists())

        # Test loading full structure
        loaded_scenarios, loaded_targets, d_rt, d_err = load_sla_scenarios_and_targets(self.test_jmx)
        self.assertEqual(len(loaded_scenarios), 2)
        self.assertEqual(loaded_scenarios[0]["name"], "Normal Load")
        self.assertEqual(loaded_scenarios[0]["users"], 50)
        self.assertEqual(loaded_scenarios[1]["name"], "Peak Load")
        self.assertEqual(loaded_scenarios[1]["users"], 200)

        # Test loading with actual_users = 45 (Nearest to Normal Load 50)
        res_targets_normal, def_rt_normal, def_err_normal = load_sla_targets(self.test_jmx, actual_users=45)
        self.assertEqual(def_rt_normal, 300.0)
        self.assertEqual(def_err_normal, 0.5)
        self.assertEqual(res_targets_normal["TC01_Launch"]["rt"], 150.0)
        self.assertEqual(res_targets_normal["TC01_Launch"]["err"], 0.2)
        self.assertEqual(res_targets_normal["TC01_Launch"]["matched_scenario"], "Normal Load")

        # Test loading with actual_users = 190 (Nearest to Peak Load 200)
        res_targets_peak, def_rt_peak, def_err_peak = load_sla_targets(self.test_jmx, actual_users=190)
        self.assertEqual(def_rt_peak, 600.0)
        self.assertEqual(def_err_peak, 1.5)
        self.assertEqual(res_targets_peak["TC01_Launch"]["rt"], 350.0)
        self.assertEqual(res_targets_peak["TC01_Launch"]["err"], 1.0)
        self.assertEqual(res_targets_peak["TC01_Launch"]["matched_scenario"], "Peak Load")
        self.assertEqual(res_targets_peak["TC02_Checkout"]["rt"], 1200.0)

        # Test loading without actual_users (Fallback to baseline)
        res_targets_base, def_rt_base, def_err_base = load_sla_targets(self.test_jmx)
        self.assertEqual(def_rt_base, 500.0)
        self.assertEqual(res_targets_base["TC01_Launch"]["rt"], 250.0)
        self.assertIsNone(res_targets_base["TC01_Launch"]["matched_scenario"])


if __name__ == "__main__":
    unittest.main()
