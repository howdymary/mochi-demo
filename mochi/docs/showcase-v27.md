# Three-video presentation

The project presentation is limited to three recordings. Broad layout experiments and additional weight training are outside this finishing pass. The detailed V25 viewer remains available at `/continuation-v25.html`.

1. The original archived desktop demonstration, copied without editing its contents. Its environment predates the furnished desk. It is historical footage, not part of the matched efficiency comparison.
2. The V15 parent and selected update-16 recordings for scenario 93001. Both complete the clock, drawer, laptop and globe within that study's quality limits. Steps fall from 804 to 470, a 41.54% reduction. Both panes use identical initial body states, scene and simulated time. The 16 Tinker updates train the shared model choosing walking, manipulation and recovery actions. They do not train the underlying native gait network.
3. A new physical reproduction of the V22 frozen C21 reference on known scenario 226003. The reference was selected after reviewing existing results because it qualified in 399 steps. The paper-free corner scene keeps the printer at `[0.435, 0.29, 0]` metres. The simulation performs the entire book ascent, clock, turnaround, forward descent, drawer, laptop and globe sequence without state restoration, splicing or applied base forces.

The final configuration includes controller engineering after V15. Differences between the second and third videos do not isolate weight training. This demonstration does not establish robust success across arbitrary layouts or a globally optimal step count. Rejected V22 and V25 candidates remain in their original reports.

## Rendering

The second and third videos render measured MuJoCo body positions and rotations through the existing Three.js appearance pipeline. The camera follows the robot and the visual materials are updated. Task-relevant motion is unchanged. Each video includes the full continuous recording at a labelled two-times playback speed, 1280 by 720 pixels and 24 output frames per second. A one-second finished hold is added after each full recording. The matched panes share one physical-time clock, so the faster side remains still after finishing while the other completes its attempt.

H.264 MP4 exports include silent video only. The first MP4 retains its archived encoding and playback. The public manifest records every video and poster hash, source recording hashes, exact measured steps, physical time and new-run verification. Large media and the exact new physical artifact live in Mochi-specific Modal volume paths rather than Git.

## Execution and limits

This finishing pass allows one additional physical attempt, at most 1,080 local wall seconds. It consumes zero new Tinker optimizer updates, Exa searches or past.dev calls. The existing V25 budget broker accounts for that physical attempt and its actual single-thread wall duration. Video rendering and encoding are separate local work. Modal hosts the public page and media.

From the repository root:

```sh
PYTHONPATH=mochi/src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 mochi/.venv/bin/python mochi/scripts/run_showcase_v27.py
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/prepare_showcase_v27.py
mochi/.venv/bin/python mochi/scripts/serve_showcase_v27.py
```

The physical runner refuses to overwrite its recording. Use a distinct run identity and account for a new budget before intentionally repeating it again. Keep archived studies unchanged.

Open a dedicated headless Chrome profile on CDP port 9355, then export each recorded scene:

```sh
node mochi/scripts/export_showcase_v27.mjs training
node mochi/scripts/export_showcase_v27.mjs final
```

The local export server accepts only the two declared H.264 filenames and binds to loopback. It serves public scene assets and replay files, never credentials. WebCodecs produces continuous H.264 frames; FFmpeg packages them into MP4 and optionally compresses them with `libx264 -preset fast -crf 23 -pix_fmt yuv420p`. Preserve the 24-frame-per-second time base. `package_showcase_v27.py` rejects durations that do not match the declared playback speed.

```sh
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/package_showcase_v27.py --upload
MOCHI_RELEASE=RELEASE_ID mochi/.venv/bin/modal deploy mochi/scripts/deploy_continuation_v25.py
node mochi/scripts/check_showcase_v27.mjs https://howdymary--mochi-continuation-v25-demo-web.us-east.modal.run/
```

## Service roles

Tinker supplies the real V15 post-training and model sampling behind the matched comparison. Exa supplies failure-driven research in the recorded studies. past.dev stores and retrieves sourced observations and experiment results between workflow roles. Modal executes simulation batches and training infrastructure and now serves these videos. This presentation does not manufacture fresh research-service activity or attribute engineering changes to weight training.

Numerical evidence is in `mochi/evidence/showcase-v27/physical-repeat.json` and `recordings.json`. Their generation requires actual successful recordings. All quality thresholds and the native gait weights remain unchanged.
