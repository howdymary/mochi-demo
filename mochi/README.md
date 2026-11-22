# MOCHI: Navigation Policy Learning on Cluttered Desks

## V25: balanced navigation training and the globe transition

[Current progress replay](https://howdymary--mochi-continuation-v25-demo-web.us-east.modal.run/) · [Findings](docs/continuation-v25-findings.md) · [Methods](docs/continuation-v25-methods.md)

Tinker completed 48 navigation and 16 separate task/recovery optimizer updates. On eight fresh layouts with two physics seeds, checkpoint 48 and the training-selected fixed strategy each qualified on 16/16 attempts. Checkpoint 48 used 16.0% fewer mean paired-layout steps and 14.2% less physical time. The earlier trained parent was faster still; the additional updates have not demonstrated a gain over that parent. The fitted contextual control also remains in the published comparison.

The globe approach now has a coherent assembly position, an east-facing approach and contact-gated foot-clearance correction. Slower support transfer repaired the book descent. Task checkpoint eight qualified in an uninterrupted development run with 817 steps, compared with 848 at updates four and sixteen. The original fresh task cohort then failed at laptop closure. After shared contact repair, parent and selected models each qualified on 1/6 new attempts. The selected successful fresh-layout recording completes all four tasks in 873 steps and 345.17 seconds. Its status as a post-evaluation highlight is explicit, and all failures remain available. Broader task reliability and a task-model advantage are unestablished. Heading-aware refinements remain experimental. Controller repairs receive engineering credit, not weight-training credit.

The original native gait network remains fixed. Tinker trains navigation and task-controller selection weights. Exa supplies failure-driven sources, past.dev passes source-verified findings between workflow stages, and Modal executes physical evaluation batches and authenticated training. Existing studies and deployments remain available below.

The later tracking-clearance candidate repaired a blocked drawer approach and completed the first three tasks in development, then stopped at the globe approach and missed the forward-travel quality gate. It was not promoted. Its new validation set remains sealed. The default replay retains the qualified fresh-layout four-task run, with the full 1/6-versus-1/6 task cohort and rejected candidates available for inspection.

## V23: unseen layouts, measured controls

[Latest paired demo](https://howdymary--mochi-navigation-v23-demo-web.us-east.modal.run/) · [Findings](docs/navigation-v23-findings.md) · [Methods and setup](docs/navigation-v23-methods.md) · [Numerical evidence](evidence/navigation-v23/results.json)

Can post-training improve humanoid navigation across unseen cluttered desk layouts, and does shared memory help within three attempts?

We completed fifteen real Tinker updates on a Qwen3.5-4B LoRA navigation selector. On eight unseen layouts with two physics seeds, the parent and selected model each qualified on 14/16 attempts. A training-selected fixed strategy qualified on 16/16. Training changed one final route choice, reducing that attempt from 512 to 341 steps. It did not establish better reliability or a learned obstacle-clearance rule.

The viewer shows identical layouts and initial states, actual MuJoCo body trajectories, planned routes, footprints, failures, all development checkpoints and stronger controls. Its opening case is explicitly labelled a post-evaluation highlight. Geometry is privileged. The native gait network stays fixed.

Exa supplied failure-driven sources, past.dev carried real cross-role evidence and isolated retry memories, Modal ran parallel physical experiments, and Tinker performed weight training and checkpoint sampling. First-attempt retrieval passed 14/16 with the same selected weights, matching the no-retrieval condition. Retry outcomes, costs, access checks and uncertainty are in the findings.

The separate [four-task preflight](https://howdymary--mochi-navigation-v23-demo-web.us-east.modal.run/task-preflight-v24.html) retains five uninterrupted engineering attempts. It completed clock, drawer and laptop in its strongest prefix, but did not validate the globe transition. No new task training or four-task generalization is claimed; final sequence layouts remain unopened. Previous demos remain available below.

## V22: visual materials and isolated GMR/mink tests

[Visual before/after](https://howdymary--mochi-visual-motion-v22-demo-web.us-east.modal.run/) · [Physical motion tests](https://howdymary--mochi-visual-motion-v22-demo-web.us-east.modal.run/?mode=motion) · [Findings](docs/visual-motion-v22-findings.md) · [Reproduce](docs/visual-motion-v22-methods.md)

The separate V22 viewer adds authored G1 materials, softer lighting, antialiasing and a detailed laptop display. Appearance comparisons use identical physical recordings. The original demo and all 276 frozen files remain unchanged.

Actual GMR retargeting and mink IK ran in an isolated environment. A gentler recovery controller reduced measured arm jerk by 29.1% in one matched component, with 11.7% more recovery time. Both development pairs qualified. Fresh complete-route qualification was reference 1/4, recovery candidate 2/4. Walking and turning results were mixed; GMR gait changes were not promoted. The viewer retains full attempts and failures. This is controller engineering with zero new Tinker optimizer updates.

In the only mutually qualified fresh pair, the candidate used 9 additional steps and took 5.87 seconds longer. No complete-route efficiency gain was demonstrated.

## Inkling 2 Mini: controller-research pilot

[Inkling proposal replay](https://howdymary--mochi-inkling-v21-demo-web.us-east.modal.run/) · [Findings](docs/inkling-v21-findings.md) · [Protocol](docs/inkling-v21-protocol.md) · [Exact model access](evidence/inkling-v21/access.json)

Inkling 2 Mini is connected through Tinker in an isolated backend. Five model-sampling attempts produced four structured results using recorded failures, controller code and three replay images. A separate oversized review packet was rejected before sampling and retained. past.dev carried the original proposal into the measured review; Exa supplied failure-driven research and Modal hosted the authenticated backend. This pilot performs zero new optimizer updates. The separate eight-update Qwen training study remains below.

The first proposals regressed or failed. After receiving those measurements and actual collision geometry, Inkling proposed backing farther clear of the laptop before turning. Changing the clearance target from y = 0.105 m to 0.055 m converted one uninterrupted development attempt from an ankle/laptop collision into all four tasks completed within every quality limit. The other development scenario still failed at laptop contact.

On four fresh paired scenarios, the fixed P5 reference qualified on 0/4 and the clearance proposal on 2/4. Both converted failures were ankle/laptop-base collisions. Both remaining failures occurred during laptop closing, before the changed waypoint. An additional P6 control qualified on 1/2 cases, including one where P5 failed, and fell on the other. It was not evaluated across the full four-case cohort. With no pairs where both primary versions qualified, step, time and recovery reductions are undefined. The complete reliability and step-reduction target was not met.

The replay distinguishes controller engineering from neural weight training and preserves failures, parameter changes and measured step counts. All 239 frozen source/configuration hashes remained unchanged. The pilot accounts for 24 physical attempts and 1.390 summed single-thread simulation wall-hours within its three-hour ceiling. Physics ran locally; Modal hosted the research backend. [Service receipts](evidence/inkling-v21/service-receipts.json) · [All experiments](evidence/inkling-v21/experiments.json) · [Numerical assessment](evidence/inkling-v21/assessment.json).

past.dev completed 12 writes and 17 logical recalls, including 15 verified cross-role recalls, with no pending ingestion. Exa made two searches. Tinker accounting is 87,228 actual-or-reserved tokens; the first failed structured-output call retains its conservative reservation. These are activity records rather than a billed-credit total. No new private-audience canary or search/memory ablation was run in this pilot.

## V19: paper-free desk and step-first post-training

[Latest checkpoint replay](https://howdymary--mochi-paperfree-v19-demo-web.us-east.modal.run/) · [Training run](https://github.com/howdymary/mochi-demo/actions/runs/44847672231) · [Assessment](docs/paperfree-v19-assessment.md) · [Numerical audit](docs/paperfree-v19-assessment.json)

The Post-it and its forced crossing are removed from physics, rendering, navigation and the success predicate. Ordinary flat walking connects drawer and laptop. The reward charges one point for every measured step, including turns, alignment, recovery and unfinished attempts. All time and arm-travel tie-breakers together cost at most 0.0011 points. Full-route qualification requires all four tasks, existing balance and smoothness limits, and at least 4.5 mm median moving-sole clearance on every flat walking leg. A shorter failed route cannot win.

Tinker completed eight real optimizer updates and 48 domain-gradient calls on the shared Qwen3.5-4B LoRA controller selector. Training covered walking, clock, drawer, laptop, globe and recovery decisions using 17 measured branch targets. Native gait and book-controller weights stayed fixed. The first collection had stopped at zero updates because a full-route smoothness average was applied to a short branch history. The [declared correction](docs/paperfree-v19r1-amendment.md) retains the original full-route limits and carries all previous resource usage. [Training proof](evidence/paperfree-v19r1/training-progress.json).

Development selected update 1 before opening fresh tests. Its one qualified development pair used 420 versus 436 steps, mostly through fewer alignment corrections. Updates 4 and 8 completed 0/3 development routes and were rejected.

| Final-test policy | Complete routes | Within every quality limit |
| --- | ---: | ---: |
| Parent | 1/4 | 0/4 |
| Selected update 1 | 2/4 | 2/4 |
| Fixed controller | 1/2 | 1/2 |
| Training-derived static policy | 0/2 | 0/2 |

The selected model's two qualified fresh attempts each used 417 steps. There are zero matched pairs in which both models qualified, so a paired step reduction is undefined. In the case both finished, the parent used 401 steps but exceeded the frozen native-acceleration limit. The 10% step-reduction and four-qualified-completion target was not met. The selected model's only changed common discrete choice was the clock approach. Walking remained W10 and recovery remained R4. This run does not establish improved walking strategy or low-level gait learning. [Choice audit](evidence/paperfree-v19r1/choice-audit.json).

The viewer retains twenty uninterrupted recordings across all four development checkpoints and all four fresh comparisons. It opens a fresh case by default, shows failed routes where they stopped, and breaks every attempt down into walking, turning, alignment and other movement phases. The separate [engineering comparison](https://howdymary--mochi-paperfree-v19-demo-web.us-east.modal.run/?mode=engineering) preserves the pre-training 468-to-414-step result; that 11.5% reduction is a fixed-controller engineering result rather than a Tinker gain.

Modal executed 21 new physical attempts. Total accounting, including the stopped collection and prior engineering, is 75 attempts and 7.991 simulation CPU-hours. This continuation made one Exa search and six past.dev writes and six logical recalls. Combined accounting is two searches, eight writes and eight recalls. Four identities wrote and read, with five verified cross-role recalls and a passing private-audience canary. No search or memory performance benefit was isolated. [Service evidence](evidence/paperfree-v19/service-receipts.json).

The independent audit verified all 236 frozen files, training counts, budget accounting and twenty recording hashes. The focused regression suite passed eight checks. [Reproduction commands and limitations](docs/paperfree-v19-assessment.md). A separate five-attempt [laptop contact-location diagnostic](docs/contact-geometry-v20.md) rejected all three proposed changes and did not alter this frozen comparison.

## V18: lifted footsteps, no promoted checkpoint

[Inspect stepping after the books](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/?scenario=development-185000&checkpoint=4&phase=desk) · [Complete development attempt](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/?scenario=development-185000&checkpoint=4) · [Final evaluation](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/) · [Assessment](docs/contact-v18-assessment.md) · [Numerical audit](docs/contact-v18-assessment.json)

Tinker completed 16 additional optimizer updates and 96 domain-gradient calls on the six-domain Qwen3.5-4B LoRA controller selector. Every update included walking, clock, drawer, laptop, globe and arm-recovery examples. The native ONNX gait weights stayed fixed. Training changed which walking, contact and recovery controllers the model chose.

Book traversal uses planned contact footsteps; flat-ground travel previously switched to a native gait with much lower foot clearance. The new W8 option adds a bounded, contact-gated swing correction through leg actuator targets. On all three development scenarios, trained checkpoints raised post-descent median minimum-sole clearance from approximately 2.5 mm to 4.8 mm. Moving swings increased from 116 to 128 on that leg. This is clearer physical stepping, with more steps rather than an efficiency gain.

Checkpoint 4 completed all four tasks on 2/3 development cases, including the linked continuous recording. Both completed attempts exceeded the frozen lateral-path limit. Checkpoint 1 completed 0/3 and checkpoint 16 completed 1/3; none of the trained versions completed a route within every quality limit. Development selection retained checkpoint 0, the parent.

| Final-test policy | Complete routes | Within all quality limits |
| --- | ---: | ---: |
| Parent | 1/4 | 0/4 |
| Selected checkpoint 0 | 1/4 | 0/4 |
| Fixed controller | 0/2 | 0/2 |
| Training-derived static policy | 1/2 | 0/2 |

The parent and selected final cohorts used the same saved weights and produced identical observed outcomes on all four paired cases. These repetitions establish no training gain. There were no matched qualified completions, so step, time and recovery-travel reductions are undefined. The full improvement target was not met. Laptop approach, contact and later fixture clearance remain unreliable.

The foot-lift correction also completed the first post-descent walking leg on both fresh fixed-controller cases, at approximately 4.8 mm clearance, before later task failures. That is controller-engineering evidence, not evidence that the trained selector generalized. The [fixed preflight](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/contact-v18-preflight.html?phase=desk) remains available separately and receives no training credit.

The viewer retains 20 uninterrupted recordings: four evaluated checkpoints on three development cases and all four parent/selected final pairs. Checkpoint 8 was saved and probed without physical evaluation under the pre-training runtime amendment. Each comparison uses the same scenario, physical-time clock and playback speed. The inspection link opens checkpoint 4 at a labelled 0.5×; Restart shows its full attempt. Failures and quality-limit violations remain visible.

### Training and service evidence

- Tinker: 16 completed optimizer updates, 96 finite domain-loss returns and 300,707 training-token presentations. Five states were saved. No native gait network was trained or newly trained checkpoint promoted.
- Modal: 80 completed cloud attempts, including measured branches and uninterrupted evaluations. Total accounting was 142 attempts, including 58 local engineering attempts and four interrupted stages, with 11.727 simulation CPU-hours. Limits were 160 attempts, 14 CPU-hours, 16 optimizer updates and four physics workers. These are budget records, not an invoice.
- Exa: one failure-driven search in the main research loop. Sources and their use remain in the report. No ablation establishes a search benefit.
- past.dev: six writes and eight logical recalls across four writing and four reading identities. The audience-isolation canary passed, with no pending ingestion. No ablation establishes a memory benefit.

[Execution and artifacts](https://github.com/howdymary/mochi-demo/actions/runs/44800327838) · [Training interface](docs/contact-v18-training-interface.md) · [Runtime amendment](docs/contact-v18-runtime-amendment.md) · [Compressed results](evidence/contact-v18/results.json.gz) · [Service records](evidence/contact-v18/service-receipts.json) · [Recording manifest](evidence/contact-v18/recording-manifest.json)

### past.dev challenge

Agents: research, design, execution and review used distinct instructions, author identities and explicit reader identities. Shared Mochi research and critic-private audiences were kept separate.

Layers: prompts held working context; past.dev stored sourced hypotheses, plans, observations and conclusions; versioned code held procedures; artifact storage held exact measurements and trajectories.

Results: the designer recalled the sourced hypothesis and selected a training allocation. The critic recalled the measured training and final results; the researcher recalled the resulting verdict. Source IDs were verified before resolving canonical numerical records. A separate private-canary recall checked audience isolation.

Caveats: the study did not demonstrate improved complete-route performance. The model saw identical rounded inputs with conflicting walking labels in two training states. Small cross-worker physical differences also affected some outcomes under matching action prefixes. These limits and rejected candidates remain in the audit.

### Reproduce the recordings and audit

From the repository root, with the package, visual assets and authenticated Modal profile configured below:

```sh
gh run download 44800327838 --repo howdymary/mochi-demo --name mochi-contact-v18-training-44800327838 --dir mochi/.cache/contact-v18-completed
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/build_contact_v18_preview.py --source mochi/.cache/contact-v18-completed
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/assess_contact_v18.py --source mochi/.cache/contact-v18-completed
node mochi/scripts/check_contact_v18_ui.mjs
python3 -m http.server 4120 --directory mochi/web/desk
```

Open `http://127.0.0.1:4120/contact-v18.html`. The public replay needs no service credentials. Exact model re-execution requires the retained backend checkpoints and provider access. Large trajectories stay in artifact storage rather than Git.

The independent audit verified all 212 frozen files, training counts, budget accounting and 20 public recordings. UI checks covered all seven scenarios and every available recorded version. Browser verification replayed both fresh attempts continuously, inspected all four final selected attempts and checked post-descent foot playback. The separate checkpoint 4 development verification retains its complete four-task recording and quality-limit warning. [Browser verification](evidence/contact-v18/browser-qa.json) · [UI verification](evidence/contact-v18/ui-verification.txt). The published checkpoint 4 inspection link was checked again after final deployment. [Live inspection verification](evidence/contact-v18/final-phase-qa.json) · [Published release](evidence/contact-v18/live-health.json).

Integration paths: [Tinker and research loop](src/mochi/contact_v18/train.py), [parallel MuJoCo evaluation](src/mochi/contact_v18/remote.py), [paired worker wrapper](src/mochi/contact_v18/paired_remote.py), [physical foot lift](src/mochi/contact_v18/residual.py), [laptop contact control](src/mochi/contact_v18/contact.py), and [audience-aware memory client](src/mochi/smooth_v17/finalize_memory.py).

## V17: completed training, failed transfer test

[Checkpoint replay](https://howdymary--mochi-smooth-v17-demo-web.us-east.modal.run/) · [Assessment](docs/smooth-v17-assessment.md) · [Numerical audit](docs/smooth-v17-assessment.json) · [Execution prompt](docs/smooth-v17-prompt.md) · [Previous validated study](https://howdymary--mochi-efficient-v15-demo-web.us-east.modal.run/)

Tinker completed 16 additional optimizer updates and 96 domain-gradient calls on the shared Qwen3.5-4B LoRA controller selector. Every update included walking, clock, drawer, laptop, globe and arm-recovery examples. The native ONNX gait and physical controllers stayed fixed throughout the comparison.

The development rule selected update 1, with 122 cumulative optimizer updates. Updates 4, 8 and 16 each fell on one of the three development scenarios and produced zero completions within all quality limits. They were rejected despite learning to choose a shorter clock reach.

| Four fresh final scenarios | Complete sequences | Within all quality limits |
| --- | ---: | ---: |
| Parent | 1/4 | 0/4 |
| Selected update 1 | 0/4 | 0/4 |
| Fixed controller | 2/4 | 2/4 |
| Training-derived static policy | 2/4 | 1/4 |

The target was at least 10% fewer steps and 15% less recovery joint travel, without lower completion or longer successful time. It was not met. There were no matched qualified parent/selected pairs, so an efficiency reduction is undefined. Early failures do not count as faster runs. The fixed and static controls also failed on some scenarios, showing that the underlying route is not yet reliable across this parameter range.

All four selected-model attempts completed the clock, book turnaround and forward descent, drawer and loaded Post-it crossing, then reached the laptop. They failed during laptop contact: two falls, one knee contact with the printer tray, and one hip contact with the laptop. All 24 separate component branches passed from a fixed reference trajectory's saved states on seed 103001. Their coverage is limited to that reference trajectory. The results motivate collecting and validating the actual laptop-contact states reached by the learned policy.

This checkpoint does not replace the previous validated V15 study. Four cases in one furnished layout are a small simulation pilot, with no hardware validation. The viewer retains all five development checkpoints and all four fresh parent/selected pairs, including failures. Development scenario 102001 has a complete matched replay; its status as development data is shown explicitly.

The audit verified 23 continuous recordings, matched initial states, the frozen source files, numerical summaries and resource accounting. Update 1 matched the parent's shared action prefix in all three development cases, while one completion outcome changed. Small physical differences with identical chosen actions remain unexplained and cannot be attributed to learned action selection.

### Execution and service evidence

- [Training and evaluation](https://github.com/howdymary/mochi-demo/actions/runs/44699655265): 16 optimizer updates, 96 domain-gradient calls and 247,758 training-token presentations. No native gait weights were trained.
- Modal: 223 accounted attempts and stages, including the 77-attempt starting debit. Of these, 221 completed; two older interrupted calls remain charged. Accounted CPU-hours were 14.886, including conservative carry bounds. These are budget records rather than an invoice.
- [Memory-only continuation](https://github.com/howdymary/mochi-demo/actions/runs/44735240968): completed the final source-verified review with zero additional optimizer updates or physical stages. The numerical result digest remained unchanged.
- Exa: two new searches in this study, including a failure-driven follow-up selected after the critic's verdict. Candidate methods were recorded for a future study; the frozen controllers were unchanged.

Public evidence: [compressed results](evidence/smooth-v17/results.json.gz), [service receipts](evidence/smooth-v17/service-receipts.json), [recording manifest](evidence/smooth-v17/recording-manifest.json) and [browser verification](evidence/smooth-v17/browser-qa.json). Browser verification includes continuous playback of the complete development comparison and inspection of a fresh-scenario failure and a rejected later checkpoint.

### past.dev challenge

Agents: research, design, execution and review used four writing identities and four verified reading identities, with explicit shared and critic-private audiences.

Layers: prompts hold working context; past.dev holds sourced findings and conclusions; versioned code holds procedures; exact measurements and trajectories stay in artifacts.

Results: six verified cross-role recalls within this study, plus the separately recorded cross-run recall. The critic rejected the final result. The researcher recalled that verdict, chose research on policy-generated laptop states and searched Exa. The designer recalled the sourced proposal and selected laptop-contact state collection as future work. The private-audience canary passed, with no pending ingestion.

Caveats: an oversized result record failed its first required-source recall. A compact, hash-linked summary recovered the handoff; the failed recall remains recorded. Canonical numerical payloads are resolved only after source-ID verification. Memory/search performance benefits were not isolated, and API activity is not a billed-credit total. [Recovery details](docs/smooth-v17-memory-recovery.md).

### Replay and audit

From the repository root, after the package and visual assets below are available:

```sh
gh run download 44735240968 --repo howdymary/mochi-demo --name mochi-smooth-v17-finalized-44735240968 --dir mochi/.cache/v17-finalized
mochi/.venv/bin/python mochi/scripts/build_smooth_v17_preview.py --source mochi/.cache/v17-finalized
node mochi/scripts/check_smooth_v17_ui.mjs
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/assess_smooth_v17.py --source mochi/.cache/v17-finalized
python3 -m http.server 4119 --directory mochi/web/desk
```

Open `http://127.0.0.1:4119/contact-trained.html`. Exporting retained recordings through Modal requires the owner's authenticated profile. Public web replay makes no Tinker, Exa or past.dev calls. Provider keys stay server-side. Canonical checkpoint references remain in backend artifacts.

Integration paths: [Tinker training and main research loop](src/mochi/smooth_v17/train.py), [parallel physics](src/mochi/smooth_v17/remote.py), [durable staged collection](src/mochi/smooth_v17/staged.py), [memory-only review](src/mochi/smooth_v17/finalize_memory.py), and [runtime inventory](docs/integrations.md).

### Engineering and interrupted runs before V17

[Execution prompt](docs/smooth-v17-prompt.md) · [Controller evidence](evidence/smooth-v17/engineering.json) · [Resource reconciliation](evidence/smooth-v17/carried-budget.json) · [Existing route preview](https://howdymary--mochi-smooth-v16-engineering-web.us-east.modal.run/)

The revised fixed reference completed the uninterrupted clock, book turnaround, forward descent, drawer, loaded Post-it crossing, laptop and globe sequence in 339.60 physical seconds and 470 steps. It passed the unchanged quality checks with no fall or forbidden contact. This was a controller-engineering result before V17 training. It did not establish reliability across the later final-test scenarios.

Three actions address measured limitations. H0 adds a joint-rest prior to clock inverse kinematics; a matched development case reduced R4 recovery travel from 9.06 to 3.62 rad. P4 uses steady 0.60 N laptop control with a 16-second action horizon; it closed the hard development case in 12.72 seconds with 0.619 N peak contact force. W6 adds a bounded globe-leg turning/speed profile; a matched development branch used 122 steps versus 138. The global force limit stays 0.8 N. Every model checkpoint and baseline receives the same extended library. Native gait weights remain fixed.

Execution [44669222147](https://github.com/howdymary/mochi-demo/actions/runs/44669222147) timed out in collection. Execution [44686221838](https://github.com/howdymary/mochi-demo/actions/runs/44686221838) preserved its physical states but stopped when none of the original laptop actions succeeded on one training approach. Both completed zero optimizer updates. Their failures and checkpoints remain archived.

V17 continued against the budget opened by the second execution, with an audited starting debit of 77 attempts and 3.870 accounted CPU-hours. This includes conservative bounds for two interrupted calls and old supervisors. It did not reset previous usage. The limits remained 224 attempts, 18 accounted CPU-hours, 16 optimizer updates and four physics workers. The old route viewers and forecasting application are preserved.

Training used historical parent-prefix states plus newly measured clock, laptop and recovery alternatives. Final evaluations were uninterrupted rollouts from reset. Every checkpoint received the same manually engineered library, and the study included fixed and training-derived static controls.

## Completed V15 walking and task-control study

[Uninterrupted checkpoint comparison](https://howdymary--mochi-efficient-v15-demo-web.us-east.modal.run/) · [Fresh test scenario](https://howdymary--mochi-efficient-v15-demo-web.us-east.modal.run/?scenario=held-out-93000) · [Technical blog](https://howdymary.github.io/mochi/) · [Assessment](docs/efficient-v15-assessment.md) · [Numerical assessment](docs/efficient-v15-assessment.json)

Tinker completed **16 new optimizer updates and 96 domain-gradient calculations** for the shared Qwen3.5-4B LoRA decision model. Every update included walking, clock, drawer, laptop, globe and arm-recovery examples. Checkpoints 0, 1, 4, 8 and 16 were evaluated on all three development scenarios. The frozen rule selected update 16 before opening four fresh final-test scenarios.

Update 0 restores a previously trained checkpoint with 105 cumulative updates. The selected checkpoint has 121 cumulative updates. The native ONNX gait, physical controllers, scene, route, step detector and success criteria stayed fixed throughout this comparison. Tinker trained controller selection, including walking commands and task/recovery profiles.

| Final-test policy | Complete within quality limits | Mean step attempts | Physical seconds |
|---|---:|---:|---:|
| Parent | 4/4 | 806.0 | 266.4 |
| Selected update 16 | 4/4 | 476.5 | 219.5 |
| Fixed controller | 4/4 | 809.5 | 264.9 |
| Training-derived static | 4/4 | 482.0 | 219.1 |

The declared 20% step-reduction target was met on this cohort. Across the four matched successful pairs, the selected model used **40.9% fewer steps** and **17.6% less simulated time** than the parent. No policy fell or made a forbidden contact in these final tests. Completion rates were equal at 4/4.

The paired bootstrap intervals are 39.4% to 41.8% for steps and 15.7% to 18.7% for time. They describe four fixed-layout cases. A 4/4 completion result has an approximately 51% to 100% Wilson interval at 95% confidence. This is a small simulation study without hardware validation.

### Static control and motion tradeoffs

The training-derived static policy was close: 482.0 steps and 219.1 seconds, compared with 476.5 steps and 219.5 seconds for the selected model. Their choices matched in 46/48 corresponding decisions. The two differences were laptop profiles on seeds 93000 and 93003. No meaningful adaptive-policy advantage was established. Small cost differences under identical choice vectors remain unexplained.

Average total arm-joint travel per successful recovery increased from 5.54 to 6.93 radians. Mean torso roll RMS increased slightly, from 0.271 to 0.279 degrees. Both remained within the declared limits. Fewer footsteps did not establish lower arm travel or smoother motion in every measure.

### Development checkpoint progression

| New updates | Qualified development completions | Mean steps | Physical seconds |
|---|---:|---:|---:|
| 0 | 3/3 | 805.3 | 265.5 |
| 1 | 3/3 | 583.3 | 237.9 |
| 4 | 3/3 | 494.7 | 219.0 |
| 8 | 3/3 | 488.0 | 218.2 |
| 16 | 3/3 | 485.3 | 218.1 |

The viewer retains all five versions on all three development scenarios, plus every parent/selected final-test pair. Each pane is one uninterrupted clock, drawer, laptop and globe episode with identical initial conditions and playback speed. Body motion and object outcomes come from recorded MuJoCo physics.

### Component checks

The first qualified fixed reference route supplied twelve supported physical states. Both models were tested from each state, producing **24 diagnostic branches**. All branches passed the frozen branch validity checks. These branches are separate from the continuous four-task tests.

Across the four walking branches, measured attempts fell from 808 to 472 and total physical time fell from 229.04 to 184.86 seconds. The laptop approach used 324 versus 172 steps from the same state. Task-plus-fixed-withdrawal time summed to 35.81 versus 32.51 seconds. Recovery time summed to 6.65 versus 5.30 seconds, while summed arm-joint travel increased from 22.15 to 26.77 radians. These totals combine separate branches, not one route.

### Execution and sponsor integrations

- Tinker: 16 completed optimizer updates, 96 gradient calculations, 217,812 training-token presentations and retained parent/intermediate states. Training examples include reuse of 48 measured observation records.
- Modal: 204 physical rollouts and 10.341 function CPU-hours, within the 224-rollout, 18-hour and four-worker limits. This reports function execution at the declared CPU allocation, not an invoice.
- Exa: one search in the research loop, selected from measured turning and alignment failures. Source URLs and provenance remain in the public report.
- past.dev: six writes and seven logical recalls, including one cross-run recall. The completed handoff includes results, critic review, a qualified conclusion and a subsequent research recall.

The 204 physical rollouts comprise one preflight, 148 data-generation branches/continuations, fifteen development episodes, sixteen final episodes and twenty-four component branches. No extra gradients or physical rollouts were needed for publication.

### past.dev challenge

**Agents:** research, design, execution and review use distinct service identities with explicit shared and private audiences.

**Layers:** prompts contain working context; past.dev stores observations, sourced hypotheses and qualified conclusions; code contains procedures; artifact storage contains exact numerical records and trajectories.

**Results:** four writing identities, four verified reading identities and five source-verified cross-role handoffs within V15. A separate cross-run recall retrieved the earlier assessment. The private-canary denial test passed, with no pending ingestions.

**Caveats:** canonical journal payloads are used after verifying returned source IDs. The study did not isolate a causal benefit from memory or search. API activity is distinct from billed credits.

### Replay and audit

Run from the repository root after the environment and visual-asset setup below. Downloading the public artifact reuses archived trajectories:

```sh
gh run download 44625135986 --repo howdymary/mochi-demo --name mochi-efficient-v15-public-44625135986 --dir mochi/web/desk/efficient-v15
python3 -m http.server 4118 --directory mochi/web/desk
```

Open `http://127.0.0.1:4118/efficient-trained.html`. To audit the retained numerical evidence:

```sh
gh run download 44625135986 --repo howdymary/mochi-demo --name mochi-efficient-v15-training-44625135986 --dir mochi/.cache/v15-completed
node mochi/scripts/check_efficient_evidence.mjs
node mochi/scripts/check_efficient_v15_ui.mjs
mochi/.venv/bin/python mochi/scripts/assess_efficient_v15.py --source mochi/.cache/v15-completed
```

[Frozen methods](docs/efficient-v15.md) · [Execution and artifacts](https://github.com/howdymary/mochi-demo/actions/runs/44625135986) · [past.dev and Tinker article draft](docs/past-dev-blog-draft.md)

Policy reruns require access to the retained Tinker states and backend credentials. Replays load the archived trajectories. Forecasting code, deployments, old checkpoints and earlier studies remain preserved.

## Completed terrain study (V12) and navigation refinement (V14)

[Turning and forward-walking comparison](https://howdymary--mochi-directional-v14-demo-web.us-east.modal.run/?case=desk-corner) · [Navigation changes and evidence](docs/directional-v14.md)

The directional navigator turns toward the next corridor, walks forward, then aligns for the task. Its replay uses actual MuJoCo body orientations. This controller refinement is evaluated separately from the frozen Tinker checkpoint study below; it adds no model-training updates.

The furnished-desk controller now completes the continuous **clock → drawer → laptop close → globe** sequence, including book ascent and descent, without hitting the clock. Two local engineering references and the subsequent remote reference passed the strict checks.

[V12 checkpoint comparison](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/terrain-trained.html) · [Recorded repaired route](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/terrain.html) · [V12 methods](docs/terrain-v12.md) · [V12 execution status](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/api/terrain-training)

Those passes establish physical feasibility. V12 completed **32 new optimizer updates and 192 domain-gradient calls** using the recorded physical comparisons, with durable checkpoints at 0, 1, 8 and 32. The first matched development comparison passed 2/3 complete smooth sequences with the parent and 3/3 after one update. The eight- and 32-update checkpoints also passed 3/3. The frozen rule selected update 1 for its lower torso roll among successful checkpoints. On six final-test scenarios, the parent completed 3/6, selected checkpoint 6/6 and fixed controller 5/6. These are small simulated cohorts; component checks did not establish learned manipulation or recovery improvement in V12. [Completed assessment](docs/terrain-v12-assessment.md). The native gait network remains fixed. Earlier V8 training and rejected V11 evidence below are preserved.

<!-- MOCHI_CURRICULUM_START -->
## Archived V8: learning walking, task and arm-recovery decisions

[Interactive before/after demo](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/) · [V8 methods](docs/control-v8-study.md) · [Numerical evidence](evidence/control-v8/results.json) · [Training execution](https://github.com/howdymary/mochi-demo/actions/runs/44382265039) · [Archived V7 viewer](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/?study=v7)

A 22.1 cm Unitree G1 walks around one desk, silences an alarm, closes a drawer and laptop, then aligns a globe. Each displayed checkpoint is a separate uninterrupted MuJoCo episode. The interface replays the recorded robot and object transforms, with synchronized before/after views and actual model decisions. Select development scenario 24001 and “Play all checkpoints” to inspect the full sequence from update 8 onward; scenario 24000 retains the laptop failure, and the development cohort remains 1/2.

Tinker completed **64 additional optimizer updates and 384 domain-gradient calls**, resuming the retained V7 update-96 state. Every update trains walking commands, all four task-profile choices and active-arm recovery. The Qwen3.5-4B LoRA selector reads simulation state. The native gait network, standing balance, arm IK and physical motion primitives remain fixed. This is command/profile learning, not learning motor torques or gait-network weights.

Development selection chose **8 additional updates**. Counts describe the whole training campaign; the selected checkpoint may precede update 64. The latest checkpoint is not automatically the selected one. Checkpoints 0/8/16/32/64, including regressions, are retained and shown.

| Four matched held-out scenarios | Parent weights, V8 setup | Selected V8 weights | Fixed controller |
|---|---:|---:|---:|
| Complete four-task sequences | 0/4 | 4/4 | 4/4 |
| Walking stations reached | 0/16 | 16/16 | 16/16 |
| Falls | 0 | 0 | 0 |
| Valid arm recoveries / attempts | 0/0 | 16/16 | 16/16 |

Four scenarios and one training run are a small simulation pilot. Walking failures can prevent later tasks from being attempted. Task success, recovery success and full-sequence success are distinct checks. Raw paired outcomes and uncertainty are in the evidence. The original V7 stack is evaluated separately; its engineering differences are not attributed to weight training.


Separate task and recovery probes use the same held-out seed block after checkpoint selection. Recovery choices start from shared post-task states, so walking failure cannot hide them. starting model: 12/16 valid recoveries. post trained model: 16/16 valid recoveries. Across 12 shared states where both recoveries passed, mean hand travel was 9.3 cm before and 9.3 cm after. These isolated resets are not part of the continuous demo. [Probe evidence](evidence/control-v8/isolated-controls.json).

### What was fixed before training

The old laptop press could not sustain enough closing torque. The new controller contacts the upper lid edge from a front-right stance, applies bounded actuator force, then withdraws while gravity finishes closing. The hinge, object properties and success criteria remain unchanged.

A universal parking detour caused unnecessary arm travel. The revised options include direct folding where safe and outward shoulder clearance before lowering beside the alarm. These are engineered primitives. Tinker learns which commands and primitives to choose; their implementation is frozen across the weight comparison. Recovery checks include stable joints, low speed, no fall and no fixture-contact steps above 0.01 N.

The recovery primitives were checked on training-only branches before learning. Across 22 shared states where both choices passed, the parking-detour option averaged 19.6 cm of hand travel; the chosen safe labels averaged 9.3 cm. This measures the engineered alternatives, not a held-out gain from trained weights. [Design audit](evidence/control-v8/recovery-design-audit.json).

### Services used

- **Tinker:** real supervised post-training, completed forward/backward and optimizer calls, durable intermediate states, and fixed-checkpoint inference in closed-loop simulation. No extra optimizer updates are credited to evaluation-only probes.
- **Modal:** 335 physical rollouts across the training/evaluation evidence, bounded at four CPU workers per function. The before/selected/fixed comparisons share one worker per scenario. Small MuJoCo experiments run on CPUs.
- **Exa:** 2 searches inside the research/training loop. Retrieved evidence informs bounded proposals; it is not executed as code.
- **past.dev:** 11 writes, 11 recall requests and 10 source-verified cross-role handoffs. Recalled proposals select between predeclared training allocations. Credit charges are not available from these API receipts.

### past.dev challenge

**Agents:** research, policy design, experiment execution and criticism use separate identities and explicit audiences.

**Layers:** prompts hold working context; past.dev stores sourced findings, outcomes and qualified conclusions; versioned code stores procedures; Mochi artifacts store numerical measurements and trajectories.

**Results:** 4 writing identities, 4 verified reading identities and 10 cross-role recalls. Private critic audience isolation passed.

**Caveats:** canonical payloads are resolved only after verifying returned source IDs. No causal memory or search ablation is claimed. Training examples include repetitions, not new market or physical observations at each update.

### Inspect and run

Run from the repository root. Provider credentials stay on the backend, using the repository's existing GitHub Actions secrets.

```sh
PYTHONPATH=mochi/src python -m pytest mochi/tests/test_control_v8.py -q
node mochi/scripts/check_replay_ui.mjs
python3 -m http.server 4028 --directory mochi/web/desk
PYTHONPATH=mochi/src python -m mochi.control_v8.train
```

The training command starts a new research run and requires access to the retained parent checkpoint. Canonical trained states remain in the owner's Tinker account; public receipts identify them by hash. Archived trajectories can be replayed without service credentials. The numerical evidence and execution artifacts support inspection; trained state access is required for an exact policy rerun.

No checkpoint deletion or billing-plan changes are part of this training study. Forecasting code, deployments and archived results remain separate. The older V6/V7 studies and their failures remain in their original evidence directories.

Integration paths: [training](src/mochi/control_v8/train.py), [Modal execution](src/mochi/control_v8/remote.py), [physical controls](src/mochi/control_v8/manipulation.py), [recovery](src/mochi/control_v8/recovery.py), [memory](src/mochi/desk/services.py), [search](src/mochi/integrations.py).
<!-- MOCHI_CURRICULUM_END -->

## Fresh environment and rendering

Reuse `mochi/.venv` when available. For a new environment, run from the repository root:

```sh
uv venv --python 3.11 mochi/.venv
uv pip install --python mochi/.venv/bin/python torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python mochi/.venv/bin/python -e './mochi[remote,dev,plots]' pyyaml==6.0.2
mochi/.venv/bin/python mochi/scripts/fetch_visual_models.py
```

See [the integration inventory](docs/integrations.md) for local versus remote credentials. The additive Mochi workflows inject existing backend secret references. The local replay server requires no provider credentials.

```sh
blender -b -t 4 -P mochi/scripts/render_curriculum.py -- \
  --input mochi/web/desk/curriculum/v8-held-out-25000-after.json \
  --out mochi/artifacts/inspection --time 53.394657 --samples 32 --camera follow
```

The source-study render uses actual selected-checkpoint motion. Use `--camera side` or `feet` to inspect gait, or `--animate` to save the recorded animation in a Blender scene. Large generated outputs and caches stay out of Git.

## Provenance and limits

This is a fixed-layout, state-observation simulation study. Waist and fingers are fixed. There is no camera input or hardware validation. Remote model inference pauses simulation time; displayed completion times exclude those waits. Sampled clearance checks do not certify continuous collision freedom.

The original supported puck slice is in [the initial archive](docs/archive/initial-puck-slice.md). The preceding navigation/planning README is [preserved separately](docs/archive/planning-v1-readme.md). Later walking, task and recovery training is not all claimed as work built during the original hackathon.

Dependencies include MuJoCo, NumPy, SciPy, PyTorch, Three.js, Blender, FastAPI and the provider SDKs. Robot hashes and licenses are recorded in [G1 provenance](assets/robot/g1/source.json) and [locomotion provenance](assets/robot/locomotion/source.json). [Scene attribution](web/desk/assets/sand3d-attribution.json) records visual assets. Forecasting code, deployments and archived results remain separate.

## Furnished-desk continuation (V11)

[Balance experiments](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/balanced.html)
retain complete attempts, failed endings and contact faults. The legacy task
counter passed three runs, but the robot hit the clock during walking. An
independent audit invalidated that reference and the pending Tinker campaign
was cancelled before gradients. Four subsequent strict Modal tests all failed.

The local 64-attempt calibration cap is reached. The remote ledger holds 155
used-or-reserved rollout slots, including a conservative 148-slot reservation
for the cancelled batch; seven completed receipts are available. No V11
trained checkpoint or fresh held-out improvement is claimed. The current
need is a terrain-capable controller that can climb without fixture support.

[Results and exact receipts](docs/balanced-v11-results.md) ·
[Methods and inspection commands](docs/balanced-v11.md) ·
[Contact audit](evidence/balance-v11/reference-audit.json).
