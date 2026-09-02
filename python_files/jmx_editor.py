#!/usr/bin/env python3
"""
jmx_editor.py — JMX XML Parser & Editor for the PerfPilot Platform.

Reads and modifies Apache JMeter .jmx test plan files to:
  - Extract ThreadGroup configurations (users, duration, rampup)
  - Update load parameters directly in the XML
  - Extract sampler/transaction labels for SLA mapping
  - Fix CSV Data Set file paths to local Tests/ directory
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


_ROOT_DIR = Path(__file__).parent.parent.resolve()
_TESTS_DIR = _ROOT_DIR / "Tests"


def read_jmx_config(jmx_path: Path) -> dict:
    """
    Parse a JMX file and extract its ThreadGroup configuration.
    Returns a dict with users, duration, rampup, loop_count, and labels.
    """
    try:
        tree = ET.parse(jmx_path)
        root = tree.getroot()
    except Exception as e:
        return {"error": f"Failed to parse JMX: {e}"}

    thread_groups = []
    tg_index = 0
    for tg in root.iter():
        if tg.tag not in ("ThreadGroup", "PostThreadGroup", "SetupThreadGroup"):
            continue

        tg_name = tg.attrib.get("testname", tg.tag)
        tg_enabled = tg.attrib.get("enabled", "true").lower() == "true"
        config = {
            "index": tg_index,
            "name": tg_name,
            "enabled": tg_enabled,
            "users": 1,
            "rampup": 0,
            "duration": 0,
            "loop_count": 1,
            "iterations": 1,
            "scheduler": False
        }

        for child in tg:
            prop_name = child.attrib.get("name", "")
            if prop_name == "ThreadGroup.num_threads":
                try:
                    config["users"] = int(child.text or "1")
                except ValueError:
                    config["users"] = 1
            elif prop_name == "ThreadGroup.ramp_time":
                try:
                    config["rampup"] = int(child.text or "0")
                except ValueError:
                    config["rampup"] = 0
            elif prop_name == "ThreadGroup.duration":
                try:
                    config["duration"] = int(child.text or "0")
                except ValueError:
                    config["duration"] = 0
            elif prop_name == "ThreadGroup.scheduler":
                config["scheduler"] = (child.text or "").lower() == "true"
            elif prop_name == "ThreadGroup.main_controller":
                for subchild in child:
                    if subchild.attrib.get("name") == "LoopController.loops":
                        try:
                            val = subchild.text or "1"
                            loop_val = -1 if val == "-1" else int(val)
                            config["loop_count"] = loop_val
                            config["iterations"] = loop_val
                        except ValueError:
                            config["loop_count"] = 1
                            config["iterations"] = 1

        thread_groups.append(config)
        tg_index += 1

    # Extract sampler labels and transaction controllers
    labels = set()
    transactions = set()

    for elem in root.iter():
        # HTTP Samplers
        if elem.tag in ("HTTPSamplerProxy", "HTTPSampler", "HTTPSampler2"):
            name = elem.attrib.get("testname", "")
            if name:
                labels.add(name)
        # Transaction Controllers
        if elem.tag == "TransactionController":
            name = elem.attrib.get("testname", "")
            if name:
                transactions.add(name)
        # JSR223 Samplers, JDBC, etc.
        if "Sampler" in elem.tag:
            name = elem.attrib.get("testname", "")
            if name:
                labels.add(name)

    # Extract CSV Data Sets & check local existence in Tests/
    csv_files = []
    missing_csv_count = 0
    for elem in root.iter():
        if elem.tag == "CSVDataSet":
            csv_name = elem.attrib.get("testname", "CSV Data Set")
            filename_val = ""
            for child in elem:
                if child.attrib.get("name") == "filename":
                    filename_val = child.text or ""

            raw_clean = (filename_val or "").strip("\r\n\t ")
            base_csv_name = Path(raw_clean.replace("\\", "/")).name if raw_clean else ""
            
            # Check case-insensitive existence in Tests/
            exists = False
            if base_csv_name and _TESTS_DIR.exists():
                for f in _TESTS_DIR.iterdir():
                    if f.is_file() and f.name.lower() == base_csv_name.lower():
                        exists = True
                        base_csv_name = f.name  # Use exact file system casing
                        break

            if not exists and base_csv_name:
                missing_csv_count += 1

            csv_files.append({
                "name": csv_name,
                "raw_path": filename_val,
                "filename": base_csv_name,
                "exists": exists
            })

    # Extract TC hierarchy mapping (Transaction Controller -> child HTTP Samplers)
    try:
        from python_files.sla_manager import parse_jmx_hierarchy
        tc_ordered, tc_to_samplers = parse_jmx_hierarchy(jmx_path)
    except Exception:
        tc_ordered, tc_to_samplers = sorted(list(transactions)), {}

    return {
        "thread_groups": thread_groups,
        "labels": sorted(list(labels)),
        "transactions": tc_ordered if tc_ordered else sorted(list(transactions)),
        "tc_to_samplers": tc_to_samplers,
        "csv_files": csv_files,
        "missing_csv_count": missing_csv_count,
        "primary_config": thread_groups[0] if thread_groups else {
            "users": 1, "rampup": 0, "duration": 0, "loop_count": 1
        }
    }


def update_jmx_config(jmx_path: Path, users: int, duration_secs: int, rampup_secs: int) -> bool:
    """
    Modify ThreadGroup configurations directly inside the JMX XML file.
    Updates num_threads, ramp_time, duration, and scheduler settings.
    Returns True if modifications were made.
    """
    try:
        tree = ET.parse(jmx_path)
        root = tree.getroot()
        modified = False

        for thread_group in root.iter():
            if thread_group.tag not in ("ThreadGroup", "PostThreadGroup", "SetupThreadGroup"):
                continue

            has_scheduler = False
            has_duration = False

            for child in thread_group:
                prop_name = child.attrib.get("name")
                if prop_name == "ThreadGroup.num_threads":
                    child.text = str(users)
                    modified = True
                elif prop_name == "ThreadGroup.ramp_time":
                    child.text = str(rampup_secs)
                    modified = True
                elif prop_name == "ThreadGroup.duration":
                    child.text = str(duration_secs)
                    has_duration = True
                    modified = True
                elif prop_name == "ThreadGroup.scheduler":
                    child.text = "true" if duration_secs > 0 else "false"
                    has_scheduler = True
                    modified = True
                elif prop_name == "ThreadGroup.main_controller":
                    for subchild in child:
                        sub_name = subchild.attrib.get("name")
                        if sub_name == "LoopController.loops":
                            if duration_secs > 0:
                                subchild.text = "-1"
                            modified = True

            # Ensure scheduler and duration elements exist if duration is set
            if duration_secs > 0:
                if not has_scheduler:
                    sched_elem = ET.Element("boolProp", {"name": "ThreadGroup.scheduler"})
                    sched_elem.text = "true"
                    thread_group.append(sched_elem)
                    modified = True
                if not has_duration:
                    dur_elem = ET.Element("longProp", {"name": "ThreadGroup.duration"})
                    dur_elem.text = str(duration_secs)
                    thread_group.append(dur_elem)
                    modified = True

        # Fix CSV Data Set file paths to point to local Tests/ directory
        for elem in root.iter():
            if elem.tag == "CSVDataSet":
                for child in elem:
                    if child.attrib.get("name") == "filename":
                        old_path_str = (child.text or "").strip("\r\n\t ")
                        if old_path_str:
                            csv_name = Path(old_path_str.replace("\\", "/")).name
                            # Check case-insensitive local file match
                            target_csv = _TESTS_DIR / csv_name
                            if not target_csv.exists() and _TESTS_DIR.exists():
                                for f in _TESTS_DIR.iterdir():
                                    if f.is_file() and f.name.lower() == csv_name.lower():
                                        target_csv = f
                                        break
                            if target_csv.exists():
                                child.text = str(target_csv)
                                modified = True

        if modified:
            tree.write(jmx_path, encoding="utf-8", xml_declaration=True)
            return True
    except Exception as e:
        print(f"[JMXEditor] Error updating JMX: {e}", flush=True)

    return False


def update_jmx_thread_groups(jmx_path: Path, thread_group_configs: list) -> bool:
    """
    Update each ThreadGroup independently inside the JMX XML file.
    
    thread_group_configs is a list of dicts, each with:
        - name: str (matches ThreadGroup testname attribute)
        - users: int
        - duration: int (seconds, 0 = use iterations)
        - rampup: int (seconds)
        - iterations: int (loop count, -1 = infinite)
    
    Returns True if any modifications were made.
    """
    try:
        tree = ET.parse(jmx_path)
        root = tree.getroot()
        modified = False

        # Build a lookup: tg_name -> config
        config_map = {}
        for idx, cfg in enumerate(thread_group_configs):
            name = cfg.get("name", "")
            if name:
                config_map[name] = cfg
            # Also support index-based matching as fallback
            config_map[f"__index_{idx}"] = cfg

        tg_index = 0
        for thread_group in root.iter():
            if thread_group.tag not in ("ThreadGroup", "PostThreadGroup", "SetupThreadGroup"):
                continue

            tg_name = thread_group.attrib.get("testname", "")
            # Match by name first, then by index
            tg_cfg = config_map.get(tg_name) or config_map.get(f"__index_{tg_index}")
            tg_index += 1

            if not tg_cfg:
                continue

            # Set enabled/disabled attribute on the ThreadGroup element
            is_enabled = tg_cfg.get("enabled", True)
            if isinstance(is_enabled, str):
                is_enabled = is_enabled.lower() not in ("false", "0", "no")
            thread_group.set("enabled", "true" if is_enabled else "false")
            modified = True

            users = int(tg_cfg.get("users", 1))
            duration_secs = to_seconds(tg_cfg.get("duration", "0"))
            rampup_secs = to_seconds(tg_cfg.get("rampup", "0"))
            iterations = int(tg_cfg.get("iterations", 1))

            has_scheduler = False
            has_duration = False

            for child in thread_group:
                prop_name = child.attrib.get("name")
                if prop_name == "ThreadGroup.num_threads":
                    child.text = str(users)
                    modified = True
                elif prop_name == "ThreadGroup.ramp_time":
                    child.text = str(rampup_secs)
                    modified = True
                elif prop_name == "ThreadGroup.duration":
                    child.text = str(duration_secs)
                    has_duration = True
                    modified = True
                elif prop_name == "ThreadGroup.scheduler":
                    child.text = "true" if duration_secs > 0 else "false"
                    has_scheduler = True
                    modified = True
                elif prop_name == "ThreadGroup.main_controller":
                    for subchild in child:
                        sub_name = subchild.attrib.get("name")
                        if sub_name == "LoopController.loops":
                            if duration_secs > 0:
                                subchild.text = "-1"
                            else:
                                subchild.text = str(iterations)
                            modified = True

            # Ensure scheduler and duration elements exist if duration is set
            if duration_secs > 0:
                if not has_scheduler:
                    sched_elem = ET.Element("boolProp", {"name": "ThreadGroup.scheduler"})
                    sched_elem.text = "true"
                    thread_group.append(sched_elem)
                    modified = True
                if not has_duration:
                    dur_elem = ET.Element("longProp", {"name": "ThreadGroup.duration"})
                    dur_elem.text = str(duration_secs)
                    thread_group.append(dur_elem)
                    modified = True

        # Fix CSV Data Set file paths to point to local Tests/ directory
        for elem in root.iter():
            if elem.tag == "CSVDataSet":
                for child in elem:
                    if child.attrib.get("name") == "filename":
                        old_path_str = (child.text or "").strip("\r\n\t ")
                        if old_path_str:
                            csv_name = Path(old_path_str.replace("\\", "/")).name
                            target_csv = _TESTS_DIR / csv_name
                            if not target_csv.exists() and _TESTS_DIR.exists():
                                for f in _TESTS_DIR.iterdir():
                                    if f.is_file() and f.name.lower() == csv_name.lower():
                                        target_csv = f
                                        break
                            if target_csv.exists():
                                child.text = str(target_csv)
                                modified = True

        if modified:
            tree.write(jmx_path, encoding="utf-8", xml_declaration=True)
            return True
    except Exception as e:
        print(f"[JMXEditor] Error updating thread groups: {e}", flush=True)

    return False


def to_seconds(val) -> int:
    """Convert a duration string like '60s', '5m', '1h', or plain int to seconds."""
    val = str(val).strip().lower()
    if val.endswith("m"):
        return int(float(val[:-1]) * 60)
    if val.endswith("s"):
        return int(float(val[:-1]))
    if val.endswith("h"):
        return int(float(val[:-1]) * 3600)
    try:
        return int(float(val))
    except ValueError:
        return 0
