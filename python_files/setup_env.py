import os
import sys
import shutil
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
ENV_FILE = CONFIG_DIR / ".env"
ENV_EXAMPLE = CONFIG_DIR / ".env.example"


def parse_env_file(filepath: Path) -> list:
    """Reads .env preserving comments, blank lines, and order."""
    if not filepath.exists():
        return []
    lines = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            lines.append(line)
    return lines


def get_env_dict(lines: list) -> dict:
    env_dict = {}
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, v = stripped.split("=", 1)
            env_dict[k.strip()] = v.strip().strip('"').strip("'")
    return env_dict


def write_env_file(filepath: Path, lines: list, updates: dict):
    existing_keys = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _ = stripped.split("=", 1)
            key = k.strip()
            existing_keys.add(key)
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for k, v in updates.items():
        if k not in existing_keys:
            new_lines.append(f"{k}={v}\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def find_java_candidate() -> str:
    """Attempt to detect Java installation."""
    # 1. System JAVA_HOME
    sys_jh = os.environ.get("JAVA_HOME", "").strip().strip('"')
    if sys_jh and Path(sys_jh).is_dir() and (Path(sys_jh) / "bin" / "java.exe").exists():
        return sys_jh

    # 2. Check 'where java'
    try:
        res = subprocess.run(["where", "java"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            for line in lines:
                p = Path(line.strip())
                if p.name.lower() == "java.exe":
                    parent = p.parent.parent
                    if (parent / "bin" / "java.exe").exists():
                        return str(parent)
    except Exception:
        pass

    # 3. Standard Windows directories
    search_dirs = [
        Path("C:/Program Files/Java"),
        Path("C:/Program Files (x86)/Java"),
        Path("C:/Program Files/Eclipse Adoptium"),
        Path("C:/Program Files/Amazon Corretto"),
        Path("C:/Program Files/Microsoft"),
        Path("D:/Java"),
        Path("D:/jdk*"),
    ]
    for sdir in search_dirs:
        if sdir.is_dir():
            for child in sdir.iterdir():
                if child.is_dir() and (child / "bin" / "java.exe").exists():
                    return str(child)

    return ""


def find_jmeter_candidate() -> str:
    """Attempt to detect JMeter installation."""
    # 1. System JMETER_HOME
    sys_jm = os.environ.get("JMETER_HOME", "").strip().strip('"')
    if sys_jm and Path(sys_jm).is_dir() and (Path(sys_jm) / "bin" / "jmeter.bat").exists():
        return sys_jm

    # 2. Standard drive roots
    for drive in ["C:", "D:", "E:"]:
        dpath = Path(drive + "/")
        if dpath.exists():
            try:
                for child in dpath.iterdir():
                    if child.is_dir() and "jmeter" in child.name.lower():
                        if (child / "bin" / "jmeter.bat").exists() or (child / "bin" / "jmeter").exists():
                            return str(child)
            except Exception:
                pass

    return ""


def validate_java_home(path_str: str) -> bool:
    if not path_str:
        return False
    p = Path(path_str)
    return p.is_dir() and ((p / "bin" / "java.exe").exists() or (p / "bin" / "java").exists())


def validate_jmeter_home(path_str: str) -> bool:
    if not path_str:
        return False
    p = Path(path_str)
    return p.is_dir() and ((p / "bin" / "jmeter.bat").exists() or (p / "bin" / "jmeter").exists())


def main():
    print("-------------------------------------------------------")
    print("  [*] PerfPilot -- Environment & Dependency Setup")
    print("-------------------------------------------------------")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Create .env if missing
    if not ENV_FILE.exists():
        if ENV_EXAMPLE.exists():
            shutil.copy(ENV_EXAMPLE, ENV_FILE)
            print("  [+] Created config/.env from template.")
        else:
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write("JMETER_HOME=\nPORT=8080\nHOST=127.0.0.1\nJAVA_HOME=\n")
            print("  [+] Created new config/.env.")

    lines = parse_env_file(ENV_FILE)
    env_dict = get_env_dict(lines)
    updates = {}

    # 2. Verify / Prompt JAVA_HOME
    curr_java = env_dict.get("JAVA_HOME", "").strip()
    if not validate_java_home(curr_java):
        print("\n  [!] JAVA_HOME is not configured or invalid in config/.env")
        candidate = find_java_candidate()
        if candidate:
            print(f"  [>] Auto-detected Java at: {candidate}")
            choice = input(f"  Use detected Java? [Y/n] or enter custom path: ").strip()
            if choice.lower() in ["", "y", "yes"]:
                updates["JAVA_HOME"] = candidate
                print(f"  [OK] JAVA_HOME set to: {candidate}")
            else:
                custom = choice.strip('"').strip("'")
                if validate_java_home(custom):
                    updates["JAVA_HOME"] = custom
                    print(f"  [OK] JAVA_HOME set to: {custom}")
                else:
                    while True:
                        inp = input("  Enter valid JAVA_HOME folder (e.g. C:\\Program Files\\Java\\jdk-17): ").strip().strip('"').strip("'")
                        if validate_java_home(inp):
                            updates["JAVA_HOME"] = inp
                            print(f"  [OK] JAVA_HOME set to: {inp}")
                            break
                        elif inp == "":
                            print("  [!] Skipping JAVA_HOME (JMeter may fail if not on system PATH).")
                            break
                        else:
                            print(f"  [X] Invalid directory: '{inp}' (could not find bin/java.exe). Try again.")
        else:
            while True:
                inp = input("  Enter JAVA_HOME folder (e.g. C:\\Program Files\\Java\\jdk-17): ").strip().strip('"').strip("'")
                if validate_java_home(inp):
                    updates["JAVA_HOME"] = inp
                    print(f"  [OK] JAVA_HOME set to: {inp}")
                    break
                elif inp == "":
                    print("  [!] Skipping JAVA_HOME (JMeter may fail if not on system PATH).")
                    break
                else:
                    print(f"  [X] Invalid directory: '{inp}' (could not find bin/java.exe). Try again.")
    else:
        print(f"  [OK] JAVA_HOME: {curr_java}")

    # 3. Verify / Prompt JMETER_HOME
    curr_jmeter = env_dict.get("JMETER_HOME", "").strip()
    if not validate_jmeter_home(curr_jmeter):
        print("\n  [!] JMETER_HOME is not configured or invalid in config/.env")
        candidate = find_jmeter_candidate()
        if candidate:
            print(f"  [>] Auto-detected JMeter at: {candidate}")
            choice = input(f"  Use detected JMeter? [Y/n] or enter custom path: ").strip()
            if choice.lower() in ["", "y", "yes"]:
                updates["JMETER_HOME"] = candidate
                print(f"  [OK] JMETER_HOME set to: {candidate}")
            else:
                custom = choice.strip('"').strip("'")
                if validate_jmeter_home(custom):
                    updates["JMETER_HOME"] = custom
                    print(f"  [OK] JMETER_HOME set to: {custom}")
                else:
                    while True:
                        inp = input("  Enter valid JMETER_HOME folder (e.g. C:\\apache-jmeter-5.6.3): ").strip().strip('"').strip("'")
                        if validate_jmeter_home(inp):
                            updates["JMETER_HOME"] = inp
                            print(f"  [OK] JMETER_HOME set to: {inp}")
                            break
                        elif inp == "":
                            print("  [!] Skipping JMETER_HOME.")
                            break
                        else:
                            print(f"  [X] Invalid directory: '{inp}' (could not find bin/jmeter.bat). Try again.")
        else:
            while True:
                inp = input("  Enter JMETER_HOME folder (e.g. C:\\apache-jmeter-5.6.3): ").strip().strip('"').strip("'")
                if validate_jmeter_home(inp):
                    updates["JMETER_HOME"] = inp
                    print(f"  [OK] JMETER_HOME set to: {inp}")
                    break
                elif inp == "":
                    print("  [!] Skipping JMETER_HOME.")
                    break
                else:
                    print(f"  [X] Invalid directory: '{inp}' (could not find bin/jmeter.bat). Try again.")
    else:
        print(f"  [OK] JMETER_HOME: {curr_jmeter}")

    # 4. Save updates to .env if any
    if updates:
        lines = parse_env_file(ENV_FILE)
        write_env_file(ENV_FILE, lines, updates)
        print(f"\n  [+] Saved updated paths to config/.env.")

    print("-------------------------------------------------------\n")


if __name__ == "__main__":
    main()
