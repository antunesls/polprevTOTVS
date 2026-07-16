import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "output" / "usr001_access.json"

with REPORT_PATH.open("r", encoding="utf-8") as report_file:
    d = json.load(report_file)

# Check MATA030's browse permissions
mata030 = next((r for r in d["routines_summary"] if r["routine"].strip() == "MATA030"), None)
if mata030:
    print("MATA030 browse_permissions:")
    for bp in mata030.get("browse_permissions", []):
        feats = [f["name"] for f in bp["features"]]
        print(f"  pos={bp['pos']} op={bp['menu_oper']} avail={bp['available']} feats={feats}")
    print()
    print("MATA030 acbrowse_status:", mata030.get("acbrowse_status"))

# Check MATA010
mata010 = next((r for r in d["routines_summary"] if r["routine"].strip() == "MATA010"), None)
if mata010:
    print("\nMATA010 browse_permissions:")
    for bp in mata010.get("browse_permissions", []):
        feats = [f["name"] for f in bp["features"]]
        print(f"  pos={bp['pos']} op={bp['menu_oper']} avail={bp['available']} feats={feats}")
    print("MATA010 acbrowse_status:", mata010.get("acbrowse_status"))
