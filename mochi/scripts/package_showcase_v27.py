"""Package three genuine videos, publish hashes, and upload public media only."""
import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
directory = ROOT / "artifacts/showcase-final"
out = ROOT / "web/desk/showcase-v27"
out.mkdir(exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument("--upload", action="store_true")
args = parser.parse_args()

def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def probe(path):
    return json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate", "-of", "json", str(path)], text=True))

physical = json.loads((ROOT / "evidence/showcase-v27/physical-repeat.json").read_text())
assert physical["complete"] and physical["qualified"]
assert all(c["passed"] for c in physical["quality_checks"])
original = ROOT / "web/desk/efficient-v15"
study = json.loads((original / "manifest.json").read_text())
names = ["held-out-parent-93001-0.json.gz", "held-out-selected-93001-16.json.gz"]
sources = []
episodes = []
for name in names:
    metadata = study["recordings"][name]
    assert metadata["qualified_complete"]
    assert sha(original / name) == metadata["sha256"]
    episodes.append(json.loads(gzip.decompress((original / name).read_bytes())))
    sources.append({"file": "efficient-v15/" + name, "sha256": metadata["sha256"],
        "checkpoint_update": metadata["checkpoint_update"], "steps": metadata["steps"]["attempts"],
        "physical_seconds": metadata["duration"], "qualified_complete": True})
assert episodes[0]["scene"] == episodes[1]["scene"]
assert episodes[0]["trajectory"]["frames"][0] == episodes[1]["trajectory"]["frames"][0]
assert [s["steps"] for s in sources] == [804, 470]

files = {}
videos = []
for number, title, ident in [(1, "The first environment", "first"),
    (2, "What post-training changed", "training"), (3, "The final corner-desk run", "final")]:
    name = f"{number:02d}-{ident}"
    path = directory / (name + ".mp4")
    small = directory / (name + "-small.mp4")
    selected = small if small.exists() else path
    info = probe(selected)
    assert len(info["streams"]) == 1 and info["streams"][0]["codec_name"] == "h264"
    assert info["streams"][0]["codec_type"] == "video"
    dest = out / (name + ".mp4")
    shutil.copyfile(selected, dest)
    poster = directory / (name + ".jpg")
    shutil.copyfile(poster, out / poster.name)
    for file in [dest, out / poster.name]:
        files[file.name] = {"sha256": sha(file), "bytes": file.stat().st_size}
    duration = float(info["format"]["duration"])
    if number > 1:
        physical_duration = max(e["duration"] for e in episodes) if number == 2 else physical["physical_seconds"]
        assert abs(duration - (physical_duration + 2) / 2) < .1
    videos.append({"id": ident, "title": title, "file": dest.name,
        "poster": poster.name, "duration_seconds": duration, "playback_speed": None if number == 1 else 2,
        "width": info["streams"][0]["width"], "height": info["streams"][0]["height"],
        "scope": "Unmodified archived screen recording" if number == 1 else "Continuous recorded MuJoCo trajectory rendered in Three.js; no cuts or resets"})

report = {"project": "MOCHI", "created_date": "2026-11-21", "videos": videos, "files": files,
    "training_comparison": {"study": "mochi-efficient-v15", "scenario": 93001, "sources": sources,
        "optimizer_updates": 16, "step_reduction_percent": (804 - 470) / 804 * 100,
        "native_gait_weights_trained": False, "same_initial_state": True, "same_scene": True,
        "scope": "One matched evaluation pair; later engineering gains are separate"},
    "final": {k: physical[k] for k in ["id", "seed", "steps", "physical_seconds", "qualified", "complete", "tasks",
        "new_optimizer_updates", "native_gait_weights_trained", "artifact_sha256", "native_weights_sha256",
        "public_recording_sha256", "printer_position_m", "quality_checks", "wall_seconds", "scope"]},
    "selection_note": "The final product demonstration reproduces the V22 fresh-scenario reference with the fewest qualified steps in that comparison. It is a known-case demonstration, not a new training advantage or generalization result.",
    "rendering": {"fps": 24, "new_videos": ["training", "final"], "camera_and_material_changes_only": True,
        "trajectory_motion": "Recorded MuJoCo body positions and rotations; task-relevant movement is not animated"},
    "limits": "One additional physical rollout, maximum 1080 local wall seconds, zero new optimizer updates, zero Exa calls and zero past.dev calls. Media rendering is local."}
(out / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
(ROOT / "evidence/showcase-v27/recordings.json").write_text(json.dumps(report, indent=2) + "\n")
if args.upload:
    import modal
    volume = modal.Volume.from_name("mochi-continuation-v25-artifacts")
    run = "mochi-nav25-20261121a"
    with volume.batch_upload() as batch:
        for name in [*files, "manifest.json"]:
            batch.put_file(out / name, f"/{run}/public/showcase-v27/{name}")
        batch.put_file(directory / (physical["id"] + ".json.gz"), f"/{run}/showcase-final/raw/{physical['id']}.json.gz")
print(json.dumps({"videos": len(videos), "steps": physical["steps"], "public_bytes": sum(f["bytes"] for f in files.values()), "uploaded": args.upload}))
