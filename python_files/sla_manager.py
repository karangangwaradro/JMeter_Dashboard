#!/usr/bin/env python3
"""
sla_manager.py — SLA Threshold & Hierarchy Manager for JmeterAI.

Manages SLA target files (.csv & .xlsx), extracts Transaction Controllers
and their child HTTP Samplers from .jmx files, and checks SLA breaches (Target RT & 90th Percentile).
"""

import os
import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

_ROOT_DIR = Path(__file__).parent.parent.resolve()
_CONFIG_DIR = _ROOT_DIR / "config"
_TESTS_DIR = _ROOT_DIR / "Tests"


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


def load_sla_targets(jmx_name: str = "") -> Tuple[Dict[str, dict], float, float]:
    """
    Load SLA targets from config/sla_targets.csv / .xlsx and paired {jmx}_sla.csv files.
    Supports single JMX name or comma-separated JMX list.
    Returns: (targets_map, default_rt, default_err)
    """
    targets = {}
    default_rt = 500.0
    default_err = 1.0

    def parse_sla_row(row: dict):
        label = row.get("Transaction Label", row.get("label", "")).strip()
        if not label: return None, None
        try:
            rt = float(row.get("Target RT (ms)", row.get("rt", 500)))
        except ValueError:
            rt = 500.0
        try:
            err = float(row.get("Target Error Rate (%)", row.get("err", 1.0)))
        except ValueError:
            err = 1.0
        try:
            minor_pct = float(row.get("Minor Breach (%)", row.get("minor_pct", 100))) # 100% = 1.0x (Target RT)
        except ValueError:
            minor_pct = 100.0
        try:
            mod_pct = float(row.get("Moderate Breach (%)", row.get("mod_pct", 200))) # 200% = 2.0x Target RT
        except ValueError:
            mod_pct = 200.0
        try:
            crit_pct = float(row.get("Critical Breach (%)", row.get("crit_pct", 300))) # 300% = 3.0x Target RT
        except ValueError:
            crit_pct = 300.0

        is_critical_raw = str(row.get("Is Critical Transaction", row.get("is_critical", "0"))).strip().lower()
        is_critical = 1 if is_critical_raw in ("1", "true", "yes", "y", "critical") else 0

        item = {
            "rt": rt,
            "err": err,
            "minor_pct": minor_pct,
            "mod_pct": mod_pct,
            "crit_pct": crit_pct,
            "is_critical": is_critical
        }
        return label, item

    # 1. Load global defaults first
    global_csv = _CONFIG_DIR / "sla_targets.csv"
    if global_csv.exists():
        try:
            with open(global_csv, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    label, item = parse_sla_row(row)
                    if not label: continue
                    if label.lower() == "default":
                        default_rt = item["rt"]
                        default_err = item["err"]
                    else:
                        targets[label] = item
        except Exception as e:
            print(f"[SLA] Error reading global CSV SLA file: {e}", flush=True)

    # Fallback/supplement with XLSX if present
    xlsx_path = _CONFIG_DIR / "sla_targets.xlsx"
    if xlsx_path.exists():
        try:
            import openpyxl
            wb = openpyxl.load_workbook(xlsx_path, read_only=True)
            if "SLA Thresholds" in wb.sheetnames:
                ws = wb["SLA Thresholds"]
                headers = [str(cell).strip() if cell else "" for cell in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
                for row_vals in ws.iter_rows(min_row=2, values_only=True):
                    if not row_vals or not row_vals[0]: continue
                    row_dict = dict(zip(headers, row_vals))
                    label, item = parse_sla_row(row_dict)
                    if not label: continue
                    if label.lower() == "default":
                        if default_rt == 500.0: default_rt = item["rt"]
                        if default_err == 1.0: default_err = item["err"]
                    elif label not in targets:
                        targets[label] = item
        except Exception as e:
            print(f"[SLA] Error reading XLSX SLA file: {e}", flush=True)

    # 2. Merge scenario-specific paired CSVs if jmx_name is provided
    if jmx_name:
        jmx_items = [j.strip() for j in str(jmx_name).split(",") if j.strip()]
        for item in jmx_items:
            clean_name = Path(item).stem
            paired_csv = _TESTS_DIR / f"{clean_name}_sla.csv"
            if paired_csv.exists():
                try:
                    with open(paired_csv, mode="r", encoding="utf-8", errors="replace") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            label, item_data = parse_sla_row(row)
                            if not label: continue
                            if label.lower() == "default":
                                default_rt = item_data["rt"]
                                default_err = item_data["err"]
                            else:
                                targets[label] = item_data
                except Exception as e:
                    print(f"[SLA] Error reading paired CSV SLA file {paired_csv}: {e}", flush=True)

    return targets, default_rt, default_err


def save_sla_targets(slas_list: List[dict], jmx_name: str = "") -> str:
    """
    Save SLA targets to paired {jmx_name}_sla.csv or config/sla_targets.csv.
    Also syncs to config/sla_targets.xlsx for backward compatibility.
    """
    if jmx_name:
        clean_name = Path(jmx_name).stem
        target_csv = _TESTS_DIR / f"{clean_name}_sla.csv"
    else:
        target_csv = _CONFIG_DIR / "sla_targets.csv"

    target_csv.parent.mkdir(parents=True, exist_ok=True)

    # Save to CSV with SLA severity columns and Is Critical flag
    with open(target_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Transaction Label", "Target RT (ms)", "Target Error Rate (%)", "Minor Breach (%)", "Moderate Breach (%)", "Critical Breach (%)", "Is Critical Transaction"])
        for item in slas_list:
            lbl = item.get("label", "").strip()
            if not lbl: continue
            rt = item.get("rt", 500)
            err = item.get("err", 1.0)
            minor = item.get("minor_pct", 100.0)
            mod = item.get("mod_pct", 200.0)
            crit = item.get("crit_pct", 300.0)
            is_crit = 1 if item.get("is_critical") in (1, True, "1", "true") else 0
            writer.writerow([lbl, rt, err, minor, mod, crit, is_crit])

    # Also update Excel file in config/
    try:
        from openpyxl import Workbook
        xlsx_path = _CONFIG_DIR / "sla_targets.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "SLA Thresholds"
        ws.append(["Transaction Label", "Target RT (ms)", "Target Error Rate (%)", "Minor Breach (%)", "Moderate Breach (%)", "Critical Breach (%)", "Is Critical Transaction"])
        for item in slas_list:
            lbl = item.get("label", "").strip()
            if not lbl: continue
            rt = item.get("rt", 500)
            err = item.get("err", 1.0)
            minor = item.get("minor_pct", 100.0)
            mod = item.get("mod_pct", 200.0)
            crit = item.get("crit_pct", 300.0)
            is_crit = 1 if item.get("is_critical") in (1, True, "1", "true") else 0
            ws.append([lbl, rt, err, minor, mod, crit, is_crit])
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

                # Read users and duration from ThreadGroup properties
                tg_users = 1
                tg_duration = 0
                for child in tg_elem:
                    prop = child.attrib.get("name", "")
                    if prop == "ThreadGroup.num_threads":
                        try: tg_users = int(child.text or "1")
                        except ValueError: pass
                    elif prop == "ThreadGroup.duration":
                        try: tg_duration = int(child.text or "0")
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
