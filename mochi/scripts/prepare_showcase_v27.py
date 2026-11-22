"""Export the new physical run without changing any archived study."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

from mochi.smooth_v16.public import rounded

ROOT = Path(__file__).resolve().parents[1]
ID = "mochi-showcase-20261121-corner-repeat-226003"
directory = ROOT / "artifacts/showcase-final"
source = directory / (ID + ".json.gz")
row = json.loads(gzip.decompress(source.read_bytes()))
metadata = json.loads((directory / (ID + ".metadata.json")).read_text())
assert metadata["status"] == "completed" and metadata["complete"] and metadata["qualified"], metadata
spec = importlib.util.spec_from_file_location("v22_export", ROOT / "scripts/build_visual_v22_motion.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
checks = module.full_quality(row)
assert all(check["passed"] for check in checks), checks
episode = module.clip(row)
assert all(episode["results"][task]["success"] for task in ["alarm", "drawer", "laptop", "globe"])
assert episode["maximum_applied_base_force"] == 0
assert not episode["paper_geometry_present"]
printer = next(prop for prop in episode["scene"]["props"] if prop["name"] == "printer")
assert printer["pos"] == [.435, .29, 0], printer
out = ROOT / "web/desk/showcase-v27"
out.mkdir(exist_ok=True)
packed = gzip.compress(json.dumps(rounded(episode), separators=(",", ":")).encode(), mtime=0)
(out / "final.json.gz").write_bytes(packed)
report = {**metadata, "quality_checks": checks, "printer_position_m": printer["pos"],
    "public_recording_sha256": hashlib.sha256(packed).hexdigest(),
    "reference": "visual-motion-v22/full-parent-fresh-226003.json.gz",
    "selection_scope": "Post-evaluation choice for a product demonstration. Known scenario reproduction; not a new benchmark.",
    "replay_scope": "Full uninterrupted from-reset physical run. No splicing, state restoration or root animation."}
evidence = ROOT / "evidence/showcase-v27"
evidence.mkdir(exist_ok=True)
(evidence / "physical-repeat.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"verified": True, "steps": metadata["steps"], "physical_seconds": metadata["physical_seconds"],
    "quality_checks": len(checks), "printer_corner": True}))
