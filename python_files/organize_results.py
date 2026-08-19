#!/usr/bin/env python3
import shutil
import glob
from pathlib import Path

def organize():
    root_dir = Path(__file__).parent.parent.resolve()
    results_dir = root_dir / "Results"
    
    html_dir = results_dir / "html"
    json_dir = results_dir / "json"
    jtl_dir = results_dir / "jtl"
    
    for d in (html_dir, json_dir, jtl_dir):
        d.mkdir(parents=True, exist_ok=True)
        
    # Move HTML files
    for f_path in results_dir.glob("*.html"):
        if f_path.is_file():
            shutil.move(str(f_path), str(html_dir / f_path.name))
            
    # Move JSON files
    for f_path in results_dir.glob("*.json"):
        if f_path.is_file():
            shutil.move(str(f_path), str(json_dir / f_path.name))

    # Move JTL files
    for f_path in results_dir.glob("*.jtl"):
        if f_path.is_file():
            shutil.move(str(f_path), str(jtl_dir / f_path.name))

if __name__ == "__main__":
    organize()
