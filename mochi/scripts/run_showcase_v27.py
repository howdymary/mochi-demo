"""Reproduce the strongest qualified corner-desk controller without retraining."""
import gzip
import hashlib
import json
import signal
import time
from pathlib import Path

import modal
import mujoco

from mochi.inkling_v21.controls import apply
from mochi.paperfree_v19 import policy, sequence
from mochi.paperfree_v19.objective import qualify
from mochi.visual_motion_v22.metrics import arm_smoothness

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/showcase-final"
OUT.mkdir(parents=True, exist_ok=True)
ID = "mochi-showcase-20261121-corner-repeat-226003"
target = OUT / (ID + ".json.gz")
assert not target.exists(), "Never overwrite a physical recording"
assert mujoco.__version__ == "3.3.7"
broker = modal.Function.from_name("mochi-continuation-v25", "budget")
run = json.loads((ROOT / "configs/continuation-v25/protocol.json").read_text())["id"]
broker.remote(run, ID + "-reserve", {"physical_rollouts": 1, "simulation_cpu_hours": .3})
started = time.perf_counter()
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("Showcase rollout wall limit")))
signal.setitimer(signal.ITIMER_REAL, 1080)

def choose(w, domain, task, default, available):
    action = "W10" if domain == "walk" else "R4" if domain == "recovery" else {
        "alarm": "H0", "drawer": "C", "laptop": "P5", "globe": "G0"}[task]
    w.decisions.append({"t": float(w.d.time), "observation": policy.observation(w, domain, task),
        "action": action, "source": "Reproduction of V22 frozen C21 reference; no new optimizer updates"})
    return action

def progress(w, domain, task):
    print(json.dumps({"domain": domain, "task": task, "physical_seconds": float(w.d.time),
        "wall_seconds": time.perf_counter() - started}), flush=True)

report = {"id": ID, "seed": 226003, "new_optimizer_updates": 0,
    "scope": "Known-scenario reproducibility run of the best qualified corner-desk reference. Not a new held-out evaluation or training gain.",
    "native_gait_weights_trained": False, "status": "running"}
try:
    with apply(json.loads((ROOT / "configs/inkling-v21-selected.json").read_text())):
        row = sequence.run(226003, True, choose, capture=progress)
        qualify(row, json.loads((ROOT / "configs/paperfree-v19-training.json").read_text()))
    episode = row["episode"]
    data = gzip.compress(json.dumps(row, separators=(",", ":")).encode(), compresslevel=1, mtime=0)
    target.write_bytes(data)
    report.update(status="completed", complete=row["complete_sequence_success"], qualified=row["qualified_complete"],
        failure=row["failure"], steps=episode["steps"]["attempts"], physical_seconds=episode["duration"],
        tasks={k: v["success"] for k, v in episode["results"].items()},
        arm_smoothness=arm_smoothness(episode), maximum_applied_base_force=episode["maximum_applied_base_force"],
        artifact_sha256=hashlib.sha256(data).hexdigest(),
        native_weights_sha256=hashlib.sha256((ROOT / "assets/robot/g1-v11-policy/exported/policy.onnx").read_bytes()).hexdigest())
except BaseException as error:
    report.update(status="error", error_type=type(error).__name__, error=str(error)[:200])
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    report["wall_seconds"] = time.perf_counter() - started
    (OUT / (ID + ".metadata.json")).write_text(json.dumps(report, indent=2) + "\n")
    broker.remote(run, ID + "-actual", {"simulation_cpu_hours": report["wall_seconds"] / 3600 - .3})
    print(json.dumps(report), flush=True)
