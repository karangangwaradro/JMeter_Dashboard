#!/usr/bin/env python3
"""
sla_manager.py — SLA Threshold & Hierarchy Manager for PerfPilot.

Manages SLA target files (.csv & .xlsx), extracts Transaction Controllers
and their child HTTP Samplers from .jmx files, and checks SLA breaches (Target RT & 90th Percentile).
Supports dynamic user load scenarios and nearest-neighbor SLA matching.
"""

import os
import re
import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional

_ROOT_DIR = Path(__file__).parent.parent.resolve()
_CONFIG_DIR = _ROOT_DIR / "config"
_TESTS_DIR = _ROOT_DIR / "Tests"

_SCENARIO_COL_REGEX = re.compile(
    r"^Scenario:\s*(.*?)\s*(?:[\(\[]\s*([0-9]+)\s*(?:Users?|U)?\s*[\)\]])\s*:\s*(Target RT.*|RT|Target Error.*|Err)$",
    re.IGNORECASE
)


def get_sla_file_path(jmx_name: str = "") -> Path:
    """Get paired CSV path for a JMX file, or fallback to default config/sla_targets.csv."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if jmx_name:
        clean_name = Path(jmx_name).stem
        paired_csv = _TESTS_DIR / f"{clean_name}_sla.csv"
        if paired_csv.exists():
            return paired_csv
    
    # Check default config SLA files
    default_csv = _CONFIG_DIR / "sla_targets.csv"
    if default_csv.exists():
        return default_csv
        
    return _CONFIG_DIR / "sla_targets.xlsx"


def match_nearest_scenario(scenarios: List[dict], actual_users: Optional[float] = None) -> Tuple[Optional[dict], float]:
    """
    Find scenario whose configured users count is nearest to actual_users.
    Returns: (matched_scenario_dict, difference_users)
    """
    if not scenarios or actual_users is None:
        return None, 0.0
    try:
        act = float(actual_users)
    except (ValueError, TypeError):
        return None, 0.0

    valid_scenarios = [s for s in scenarios if "users" in s and s["users"] is not None]
    if not valid_scenarios:
        return None, 0.0

    nearest = min(valid_scenarios, key=lambda s: abs(float(s.get("users", 0)) - act))
    diff = abs(float(nearest.get("users", 0)) - act)
    return nearest, diff


def _parse_csv_header_scenarios(fieldnames: List[str]) -> Tuple[List[dict], Dict[str, Tuple[str, str]]]:
    """
    Extract load scenarios and column mappings from CSV header fields.
    Returns:
      scenarios: [{'id': '...', 'name': 'Peak Load', 'users': 200, 'rt_col': '...', 'err_col': '...'}]
      col_map: {field_name: (scenario_name_or_id, 'rt'|'err')}
    """
    scenarios_dict = {}
    col_map = {}
    if not fieldnames:
        return [], {}

    for field in fieldnames:
        f_clean = str(field).strip()
        m = _SCENARIO_COL_REGEX.match(f_clean)
        if m:
            sc_name = m.group(1).strip()
            sc_users = int(m.group(2))
            metric_type = "rt" if ("rt" in m.group(3).lower()) else "err"
            sc_key = f"{sc_name}_{sc_users}"
            if sc_key not in scenarios_dict:
                scenarios_dict[sc_key] = {
                    "id": f"sc_{re.sub(r'[^a-zA-Z0-9_]', '_', sc_name.lower())}_{sc_users}",
                    "name": sc_name,
                    "users": sc_users
                }
            if metric_type == "rt":
                scenarios_dict[sc_key]["rt_col"] = f_clean
            else:
                scenarios_dict[sc_key]["err_col"] = f_clean
            col_map[f_clean] = (sc_key, metric_type)

    scenarios = list(scenarios_dict.values())
    scenarios.sort(key=lambda s: s.get("users", 0))
    return scenarios, col_map


def load_sla_scenarios_and_targets(jmx_name: str = "") -> Tuple[List[dict], Dict[str, dict], float, float]:
    """
    Load all defined load scenarios along with full per-transaction scenario target matrix.
    Returns: (scenarios, targets_map, default_rt, default_err)
    """
    targets = {}
    scenarios = []
    default_rt = 500.0
    default_err = 1.0

    def parse_full_sla_row(row: dict, col_map: dict, scenarios_list: List[dict]):
        label = row.get("Transaction Label", row.get("label", "")).strip()
        if not label:
            return None, None
        try:
            rt = float(row.get("Target RT (ms)", row.get("rt", 500)))
        except (ValueError, TypeError):
            rt = 500.0
        try:
            err = float(row.get("Target Error Rate (%)", row.get("err", 1.0)))
        except (ValueError, TypeError):
            err = 1.0
        try:
            minor_pct = float(row.get("Minor Breach (%)", row.get("minor_pct", 100)))
        except (ValueError, TypeError):
            minor_pct = 100.0
        try:
            mod_pct = float(row.get("Moderate Breach (%)", row.get("mod_pct", 200)))
        except (ValueError, TypeError):
            mod_pct = 200.0
        try:
            crit_pct = float(row.get("Critical Breach (%)", row.get("crit_pct", 300)))
        except (ValueError, TypeError):
            crit_pct = 300.0

        is_critical_raw = str(row.get("Is Critical Transaction", row.get("is_critical", "0"))).strip().lower()
        is_critical = 1 if is_critical_raw in ("1", "true", "yes", "y", "critical") else 0

        # Scenario specific targets
        row_scenarios = {}
        for sc in scenarios_list:
            sc_id = sc["id"]
            sc_key = f"{sc['name']}_{sc['users']}"
            sc_rt_col = sc.get("rt_col")
            sc_err_col = sc.get("err_col")
            sc_rt = rt
            sc_err = err
            if sc_rt_col and sc_rt_col in row and row[sc_rt_col] != "":
                try:
                    sc_rt = float(row[sc_rt_col])
                except (ValueError, TypeError):
                    pass
            if sc_err_col and sc_err_col in row and row[sc_err_col] != "":
                try:
                    sc_err = float(row[sc_err_col])
                except (ValueError, TypeError):
                    pass
            row_scenarios[sc_id] = {"rt": sc_rt, "err": sc_err}
            row_scenarios[sc_key] = {"rt": sc_rt, "err": sc_err}
            row_scenarios[sc["name"]] = {"rt": sc_rt, "err": sc_err}

        item = {
            "rt": rt,
            "err": err,
            "minor_pct": minor_pct,
            "mod_pct": mod_pct,
            "crit_pct": crit_pct,
            "is_critical": is_critical,
            "scenarios": row_scenarios
        }
        return label, item

    # 1. Check paired CSV or global CSV
    sla_file = get_sla_file_path(jmx_name)
    if sla_file.exists() and sla_file.suffix.lower() == ".csv":
        try:
            with open(sla_file, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    scenarios, col_map = _parse_csv_header_scenarios(reader.fieldnames)
                else:
                    col_map = {}
                for row in reader:
                    label, item = parse_full_sla_row(row, col_map, scenarios)
                    if not label:
                        continue
                    if label.lower() == "default":
                        default_rt = item["rt"]
                        default_err = item["err"]
                    targets[label] = item
        except Exception as e:
            print(f"[SLA] Error loading scenario SLA from {sla_file}: {e}", flush=True)

    # Fallback to global if nothing loaded
    if not targets:
        global_csv = _CONFIG_DIR / "sla_targets.csv"
        if global_csv.exists():
            try:
                with open(global_csv, mode="r", encoding="utf-8", errors="replace") as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames:
                        scenarios, col_map = _parse_csv_header_scenarios(reader.fieldnames)
                    else:
                        col_map = {}
                    for row in reader:
                        label, item = parse_full_sla_row(row, col_map, scenarios)
                        if not label:
                            continue
                        if label.lower() == "default":
                            default_rt = item["rt"]
                            default_err = item["err"]
                        targets[label] = item
            except Exception as e:
                print(f"[SLA] Error loading global SLA: {e}", flush=True)

    return scenarios, targets, default_rt, default_err


def get_matched_scenario_info(jmx_name: str = "", actual_users: Optional[float] = None) -> dict:
    """
    Get information about which load scenario is matched for a given user count.
    """
    scenarios, _, _, _ = load_sla_scenarios_and_targets(jmx_name)
    matched_sc, diff = match_nearest_scenario(scenarios, actual_users)
    return {
        "actual_users": actual_users,
        "matched_scenario": matched_sc,
        "diff": diff,
        "all_scenarios": scenarios
    }


def load_sla_targets(jmx_name: str = "", actual_users: Optional[float] = None) -> Tuple[Dict[str, dict], float, float]:
    """
    Load SLA targets from config/sla_targets.csv / .xlsx and paired {jmx}_sla.csv files.
    If actual_users is provided, dynamically resolves SLA thresholds from the nearest load scenario.
    Returns: (targets_map, default_rt, default_err)
    """
    scenarios, raw_targets, default_rt, default_err = load_sla_scenarios_and_targets(jmx_name)
    
    # If no targets loaded at all, provide basic default
    if not raw_targets:
        raw_targets["default"] = {
            "rt": default_rt,
            "err": default_err,
            "minor_pct": 100.0,
            "mod_pct": 200.0,
            "crit_pct": 300.0,
            "is_critical": 0,
            "scenarios": {}
        }

    resolved_targets = {}
    matched_sc, _ = match_nearest_scenario(scenarios, actual_users) if (actual_users is not None and scenarios) else (None, 0.0)

    # Check if default label has scenario overrides
    active_default_rt = default_rt
    active_default_err = default_err
    if "default" in raw_targets:
        d_item = raw_targets["default"]
        if matched_sc and "scenarios" in d_item:
            sc_key = matched_sc["id"]
            sc_data = d_item["scenarios"].get(sc_key) or d_item["scenarios"].get(matched_sc["name"])
            if sc_data:
                active_default_rt = sc_data.get("rt", default_rt)
                active_default_err = sc_data.get("err", default_err)

    for label, item in raw_targets.items():
        if label.lower() == "default":
            continue
        
        tx_rt = item.get("rt", active_default_rt)
        tx_err = item.get("err", active_default_err)

        if matched_sc and "scenarios" in item:
            sc_key = matched_sc["id"]
            sc_data = item["scenarios"].get(sc_key) or item["scenarios"].get(matched_sc["name"])
            if sc_data:
                tx_rt = sc_data.get("rt", tx_rt)
                tx_err = sc_data.get("err", tx_err)

        resolved_targets[label] = {
            "rt": tx_rt,
            "err": tx_err,
            "minor_pct": item.get("minor_pct", 100.0),
            "mod_pct": item.get("mod_pct", 200.0),
            "crit_pct": item.get("crit_pct", 300.0),
            "is_critical": item.get("is_critical", 0),
            "matched_scenario": matched_sc.get("name") if matched_sc else None
        }

    return resolved_targets, active_default_rt, active_default_err


def save_sla_targets(slas_list: List[dict], jmx_name: str = "", scenarios: Optional[List[dict]] = None) -> str:
    """
    Save SLA targets and dynamic load scenarios to paired {jmx_name}_sla.csv or config/sla_targets.csv.
    Also syncs to config/sla_targets.xlsx for backward compatibility.
    """
    if jmx_name:
        clean_name = Path(jmx_name).stem
        target_csv = _TESTS_DIR / f"{clean_name}_sla.csv"
    else:
        target_csv = _CONFIG_DIR / "sla_targets.csv"

    target_csv.parent.mkdir(parents=True, exist_ok=True)
    scenarios = scenarios or []

    # Clean & normalize scenarios
    clean_scenarios = []
    for sc in scenarios:
        s_name = str(sc.get("name", "")).strip()
        try:
            s_users = int(sc.get("users", 1))
        except (ValueError, TypeError):
            s_users = 1
        s_id = sc.get("id") or f"sc_{re.sub(r'[^a-zA-Z0-9_]', '_', s_name.lower())}_{s_users}"
        if s_name:
            clean_scenarios.append({
                "id": s_id,
                "name": s_name,
                "users": s_users
            })

    # Build CSV header with scenario columns
    header = [
        "Transaction Label",
        "Target RT (ms)",
        "Target Error Rate (%)",
        "Minor Breach (%)",
        "Moderate Breach (%)",
        "Critical Breach (%)",
        "Is Critical Transaction"
    ]

    for sc in clean_scenarios:
        header.append(f"Scenario: {sc['name']} ({sc['users']} Users):Target RT (ms)")
        header.append(f"Scenario: {sc['name']} ({sc['users']} Users):Target Error Rate (%)")

    # Save to CSV with multi-scenario columns
    with open(target_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for item in slas_list:
            lbl = item.get("label", "").strip()
            if not lbl:
                continue
            rt = item.get("rt", 500)
            err = item.get("err", 1.0)
            minor = item.get("minor_pct", 100.0)
            mod = item.get("mod_pct", 200.0)
            crit = item.get("crit_pct", 300.0)
            is_crit = 1 if item.get("is_critical") in (1, True, "1", "true") else 0
            
            row = [lbl, rt, err, minor, mod, crit, is_crit]

            item_scenarios = item.get("scenarios", {})
            for sc in clean_scenarios:
                sc_id = sc["id"]
                sc_name = sc["name"]
                sc_val = item_scenarios.get(sc_id) or item_scenarios.get(sc_name) or {}
                sc_rt = sc_val.get("rt", rt)
                sc_err = sc_val.get("err", err)
                row.append(sc_rt)
                row.append(sc_err)

            writer.writerow(row)

    # Also update Excel file in config/
    try:
        from openpyxl import Workbook
        xlsx_path = _CONFIG_DIR / "sla_targets.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "SLA Thresholds"
        ws.append(header)
        for item in slas_list:
            lbl = item.get("label", "").strip()
            if not lbl:
                continue
            rt = item.get("rt", 500)
            err = item.get("err", 1.0)
            minor = item.get("minor_pct", 100.0)
            mod = item.get("mod_pct", 200.0)
            crit = item.get("crit_pct", 300.0)
            is_crit = 1 if item.get("is_critical") in (1, True, "1", "true") else 0
            
            row = [lbl, rt, err, minor, mod, crit, is_crit]
            item_scenarios = item.get("scenarios", {})
            for sc in clean_scenarios:
                sc_id = sc["id"]
                sc_name = sc["name"]
                sc_val = item_scenarios.get(sc_id) or item_scenarios.get(sc_name) or {}
                sc_rt = sc_val.get("rt", rt)
                sc_err = sc_val.get("err", err)
                row.append(sc_rt)
                row.append(sc_err)
            ws.append(row)
        wb.save(xlsx_path)
    except Exception as e:
        print(f"[SLA] Warning sync to XLSX: {e}", flush=True)

    return str(target_csv)


def parse_jmx_hierarchy(jmx_input) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Parse JMX (or comma-separated list of JMX files) to extract:
      1. Transaction Controllers (especially main TCs starting with TC / T / T01 etc.)
      2. Mapping of Transaction Controller -> List of child HTTP Samplers
    """
    tc_list = []
    tc_to_samplers = {}

    if not jmx_input:
        return tc_list, tc_to_samplers

    jmx_paths = []
    if isinstance(jmx_input, (list, tuple)):
        jmx_paths = [Path(p) for p in jmx_input]
    elif isinstance(jmx_input, Path):
        jmx_paths = [jmx_input]
    elif isinstance(jmx_input, str):
        for name in jmx_input.split(","):
            name = name.strip()
            if not name: continue
            p = Path(name)
            if not p.is_absolute():
                p = _TESTS_DIR / name
            jmx_paths.append(p)

    for jmx_path in jmx_paths:
        if not jmx_path.exists():
            continue

        try:
            tree = ET.parse(jmx_path)
            root = tree.getroot()

            all_tcs = []
            for tc_elem in root.iter("TransactionController"):
                tc_name = tc_elem.attrib.get("testname", "").strip()
                if not tc_name:
                    continue

                u_name = tc_name.upper()
                is_main_tc = u_name.startswith("TC")

                if is_main_tc:
                    if tc_name not in tc_list:
                        tc_list.append(tc_name)
                else:
                    all_tcs.append(tc_name)

                if tc_name not in tc_to_samplers:
                    tc_to_samplers[tc_name] = []

                # Traverse all sub-elements (ParallelControllers, child TransactionControllers, HTTP Samplers)
                for child in tc_elem.iter():
                    c_name = child.attrib.get("testname", "").strip()
                    if not c_name or c_name == tc_name:
                        continue
                    # Match HTTP Samplers, TransactionControllers, and Parallel Controllers
                    if "HTTPSampler" in child.tag or "TransactionController" in child.tag or "Parallel" in child.tag:
                        if c_name not in tc_to_samplers[tc_name]:
                            tc_to_samplers[tc_name].append(c_name)

            if not tc_list and all_tcs:
                for tc_n in all_tcs:
                    if tc_n not in tc_list:
                        tc_list.append(tc_n)

        except Exception as e:
            print(f"[SLA] Error parsing JMX hierarchy from {jmx_path.name}: {e}", flush=True)

    def tc_sort_key(name: str):
        u = name.upper()
        if u.startswith("TC"): return (0, name)
        if u.startswith("T01") or u.startswith("T1"): return (1, name)
        if u.startswith("T_"): return (2, name)
        return (3, name)

    tc_list.sort(key=tc_sort_key)
    return tc_list, tc_to_samplers
def parse_jmx_thread_groups(jmx_input) -> List[Dict]:
    """
    Parse JMX file(s) and return a list of ThreadGroup configs.

    Each item:
      {
        name:         str   — ThreadGroup display name (e.g. "TC01_Services")
        enabled:      bool  — Whether the TG was enabled in the JMX
        wrapper_tc:   str   — First direct TC inside TG (e.g. "T-1_Overall Iteration")
                             This is what actually appears in the JTL as a label.
        users:        int   — Configured concurrent users
        duration:     int   — Duration in seconds
        child_tcs:    list  — Named TCs inside the wrapper (the user story steps)
      }

    IMPORTANT: JMeter XML structure note:
      <ThreadGroup testname="TC01_Services">
        <intProp name="ThreadGroup.num_threads">10</intProp>   ← properties only
      </ThreadGroup>
      <hashTree>                       ← SIBLING hashTree has the actual test elements
        <TransactionController testname="T-1_Overall Iteration"/>
        <hashTree>
          <TransactionController testname="TC01Launch Home Page URL"/>
          ...
        </hashTree>
      </hashTree>

    The TCs are NOT children of the ThreadGroup element — they are in the
    sibling hashTree that immediately follows it. We must traverse the parent's
    children list to find the correct hashTree for each ThreadGroup.
    """
    result = []

    if not jmx_input:
        return result

    jmx_paths = []
    if isinstance(jmx_input, (list, tuple)):
        jmx_paths = [Path(p) for p in jmx_input]
    elif isinstance(jmx_input, Path):
        jmx_paths = [jmx_input]
    elif isinstance(jmx_input, str):
        for name in jmx_input.split(","):
            name = name.strip()
            if not name: continue
            p = Path(name)
            if not p.is_absolute():
                p = _TESTS_DIR / name
            jmx_paths.append(p)

    for jmx_path in jmx_paths:
        if not jmx_path.exists():
            continue
        try:
            tree = ET.parse(jmx_path)
            root = tree.getroot()

            def find_tg_pairs(parent_elem):
                """Walk children of parent_elem and pair each ThreadGroup with its following hashTree."""
                pairs = []
                children = list(parent_elem)
                for i, child in enumerate(children):
                    if child.tag in ("ThreadGroup", "PostThreadGroup", "SetupThreadGroup"):
                        # The next sibling is this TG's hashTree
                        tg_hash = children[i + 1] if (i + 1 < len(children) and children[i + 1].tag == "hashTree") else None
                        pairs.append((child, tg_hash))
                    # Recurse into hashTrees to find nested TGs
                    if child.tag == "hashTree":
                        pairs.extend(find_tg_pairs(child))
                return pairs

            tg_pairs = find_tg_pairs(root)

            for tg_elem, tg_hashtree in tg_pairs:
                tg_name = tg_elem.attrib.get("testname", "").strip()
                tg_enabled = tg_elem.attrib.get("enabled", "true").lower() == "true"

                # Read users, duration, and ramp-up from ThreadGroup properties
                tg_users = 1
                tg_duration = 0
                tg_rampup = 0
                for child in tg_elem:
                    prop = child.attrib.get("name", "")
                    if prop == "ThreadGroup.num_threads":
                        try: tg_users = int(child.text or "1")
                        except ValueError: pass
                    elif prop == "ThreadGroup.duration":
                        try: tg_duration = int(child.text or "0")
                        except ValueError: pass
                    elif prop == "ThreadGroup.ramp_time":
                        try: tg_rampup = int(child.text or "0")
                        except ValueError: pass

                # Search for TCs in the SIBLING hashTree (not inside tg_elem!)
                wrapper_tc = None
                child_tcs = []

                if tg_hashtree is not None:
                    all_tcs_in_tg = []
                    for tc_elem in tg_hashtree.iter("TransactionController"):
                        tc_name = tc_elem.attrib.get("testname", "").strip()
                        if tc_name:
                            all_tcs_in_tg.append(tc_name)

                    if all_tcs_in_tg:
                        # First TC is the wrapper (e.g. "T-1_Overall Iteration")
                        wrapper_tc = all_tcs_in_tg[0]
                        # Rest are user story step TCs — filter out generic names
                        child_tcs = [
                            tc for tc in all_tcs_in_tg[1:]
                            if not tc.lower().startswith("transaction controller")
                            and not tc.lower().startswith("bzm")
                            and tc != wrapper_tc
                        ]

                result.append({
                    "name":       tg_name,
                    "enabled":    tg_enabled,
                    "wrapper_tc": wrapper_tc,
                    "users":      tg_users,
                    "duration":   tg_duration,
                    "rampup":     tg_rampup,
                    "child_tcs":  child_tcs
                })

        except Exception as e:
            print(f"[SLA] Error parsing thread groups from {jmx_path.name}: {e}", flush=True)

    return result


def parse_jmx_full_tree(jmx_input) -> Tuple[List[Dict], Dict[str, List[str]]]:
    """
    Parse JMX file(s) and return a full nested tree structure preserving the
    Thread Group → Transaction Controller → Sub-Transaction → HTTP Request hierarchy.

    Returns:
        (tree, tg_to_transactions)
        - tree: list of thread group dicts, each with nested 'children':
            [
                {
                    "name": "US01_Browse_Catalog",
                    "type": "threadgroup",
                    "children": [
                        {
                            "name": "T-US01_Overall_Iteration",
                            "type": "transaction",
                            "children": [
                                {
                                    "name": "TC01_US01_Launch_Catalog",
                                    "type": "transaction",
                                    "children": [
                                        {"name": "HTTP_Launch_Catalog", "type": "request", "children": []}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        - tg_to_transactions: mapping of thread group name → list of direct TC names
            {"US01_Browse_Catalog": ["TC01_US01_Launch_Catalog", "TC02_US01_Select_Fish_Category", ...]}
    """
    tree = []
    tg_to_transactions = {}

    if not jmx_input:
        return tree, tg_to_transactions

    jmx_paths = []
    if isinstance(jmx_input, (list, tuple)):
        jmx_paths = [Path(p) for p in jmx_input]
    elif isinstance(jmx_input, Path):
        jmx_paths = [jmx_input]
    elif isinstance(jmx_input, str):
        for name in jmx_input.split(","):
            name = name.strip()
            if not name:
                continue
            p = Path(name)
            if not p.is_absolute():
                p = _TESTS_DIR / name
            jmx_paths.append(p)

    def _build_subtree(parent_children_list):
        """
        Walk a list of XML elements (children of a hashTree) and pair each
        test element with its following hashTree sibling to build a nested tree.

        JMeter XML structure:
            <hashTree>
                <TransactionController testname="TC01"/>
                <hashTree>   ← this hashTree contains TC01's children
                    <HTTPSamplerProxy testname="HTTP_1"/>
                    <hashTree/>
                    <TransactionController testname="SubTC"/>
                    <hashTree>
                        ...
                    </hashTree>
                </hashTree>
                <TransactionController testname="TC02"/>
                <hashTree>
                    ...
                </hashTree>
            </hashTree>
        """
        nodes = []
        elems = list(parent_children_list)
        i = 0
        while i < len(elems):
            elem = elems[i]
            tag = elem.tag
            test_name = elem.attrib.get("testname", "").strip()
            is_enabled = elem.attrib.get("enabled", "true").lower() == "true"

            # Determine node type
            node_type = None
            if "TransactionController" in tag:
                node_type = "transaction"
            elif "HTTPSampler" in tag:
                node_type = "request"
            elif "Parallel" in tag:
                node_type = "transaction"  # Parallel controllers act like transactions

            if node_type and test_name and is_enabled:
                # The NEXT sibling should be a hashTree with this element's children
                child_hash = None
                if i + 1 < len(elems) and elems[i + 1].tag == "hashTree":
                    child_hash = elems[i + 1]
                    i += 1  # skip the hashTree in main iteration

                children = []
                if child_hash is not None and node_type != "request":
                    children = _build_subtree(child_hash)

                nodes.append({
                    "name": test_name,
                    "type": node_type,
                    "children": children
                })
            elif tag == "hashTree":
                # Orphan hashTree (e.g. for config elements) — recurse into it
                # to catch any nested test elements
                nested = _build_subtree(elem)
                nodes.extend(nested)

            i += 1
        return nodes

    def _collect_tc_names(node, depth=0):
        """Recursively collect all transaction names from a tree node."""
        names = []
        if node.get("type") == "transaction":
            names.append(node["name"])
        for child in node.get("children", []):
            names.extend(_collect_tc_names(child, depth + 1))
        return names

    for jmx_path in jmx_paths:
        if not jmx_path.exists():
            continue

        try:
            jmx_tree = ET.parse(jmx_path)
            root = jmx_tree.getroot()

            # Find ThreadGroup elements and pair with sibling hashTrees
            def _find_tg_pairs(parent_elem):
                pairs = []
                children = list(parent_elem)
                for idx, child in enumerate(children):
                    if child.tag in ("ThreadGroup", "PostThreadGroup", "SetupThreadGroup"):
                        tg_hash = children[idx + 1] if (
                            idx + 1 < len(children) and children[idx + 1].tag == "hashTree"
                        ) else None
                        pairs.append((child, tg_hash))
                    if child.tag == "hashTree":
                        pairs.extend(_find_tg_pairs(child))
                return pairs

            tg_pairs = _find_tg_pairs(root)

            for tg_elem, tg_hashtree in tg_pairs:
                tg_name = tg_elem.attrib.get("testname", "").strip()
                tg_enabled = tg_elem.attrib.get("enabled", "true").lower() == "true"
                if not tg_name or not tg_enabled:
                    continue

                tg_children = []
                if tg_hashtree is not None:
                    tg_children = _build_subtree(tg_hashtree)

                tg_node = {
                    "name": tg_name,
                    "type": "threadgroup",
                    "children": tg_children
                }
                tree.append(tg_node)

                # Build tg_to_transactions mapping
                all_tc_names = []
                for child in tg_children:
                    all_tc_names.extend(_collect_tc_names(child))
                tg_to_transactions[tg_name] = all_tc_names

        except Exception as e:
            print(f"[SLA] Error parsing full tree from {jmx_path.name}: {e}", flush=True)

    return tree, tg_to_transactions
