# V25 continuation findings

Status: the complete 64-rollout final navigation comparison is finished. The fixed-reference goal passed. The earlier trained parent remains more efficient than checkpoint 48. Final task layouts remain unopened while the combined-model preflight runs. The [progress replay](https://howdymary--mochi-continuation-v25-demo-web.us-east.modal.run/) retains full checkpoint and engineering attempts.

## What is trained

Tinker completed 48 navigation and 16 separate task/recovery optimizer updates. Both adapters start from the exact V23 update-4 Qwen3.5-4B weights and use rank-16 LoRA. The navigation campaign began with three physically executed route/controller profiles; its final continuation selects between direct and buffered control. Task control selects bounded contact and recovery primitives. The native Unitree gait network remains fixed.

A separate numerical audit compared navigation updates 32 and 48. It found changes in all 498 exported adapter tensors, with maximum absolute change 0.00345411 and L2 change 4.95889. That confirms the compact continuation changed model parameters. It does not establish an improvement in physical performance.

The task update-16 tensor audit found changes in 498 adapter tensors, with maximum absolute change 0.00159891 and L2 change 4.03317. The original saved states are intact. Expiring exports provide numerical evidence of weight changes, not evidence of better performance by themselves. The earlier failed audit is preserved alongside the successful retry.

## Navigation development results so far

| Method | Qualified attempts | Comparison status |
| --- | ---: | --- |
| Training-selected fixed profile | 15/16 | Primary fixed reference |
| Collision-aware planner | 15/16 | Physically executed control |
| Training-fitted contextual rule | 16/16 | Stronger conditional control |
| Parent | 15/16 | Fails a case the fixed profile passes |
| Update 8 | 14/16 | Not promoted |

The parent and update 8 use fewer steps on jointly qualified attempts, but introduce new quality failures. Neither meets the predeclared reliability gate. Later checkpoints and any predeclared training extension are still being evaluated. No final-layout advantage is established.

A training-only audit of update 32 found 13 direct choices and 11 wide-fast choices, agreeing with the measured teacher on 19 of 24 training layouts. It missed the sole training layout requiring buffered control. This demonstrates conditional choices on training geometry, not successful generalization or a learned safety rule.

## Continuous task-model comparison

These are separate uninterrupted runs from reset, using the same scene, physics seed 252000, source, fixed navigation profile, contact controllers and verification.

| Task weights | All four tasks completed | Full qualification | Measured steps | Physical seconds |
| --- | --- | --- | ---: | ---: |
| Parent, update 0 | Yes | No | 966 | 357.19 |
| Update 4 | Yes | Yes | 848 | 341.63 |

The parent missed laptop-leg sole clearance: 4.395 mm against the frozen 4.5 mm requirement. Update 4 measured 4.818 mm and passed. Its earlier drawer choice changed from B to C. Subsequent navigation receives the resulting physical state; no new starting pose is inserted between tasks.

The step and time counts are descriptive. Because the parent did not qualify, this pair is a quality conversion rather than a qualified efficiency comparison. Continuous development runs, rather than matched component tests alone, determine final checkpoint selection.

The remaining continuous attempts have now finished. Update eight qualified in 817 steps and 339.07 seconds. Update sixteen qualified in 848 steps and 341.63 seconds, matching update four. Update eight is the frozen task selection. On this one jointly qualified development pair, it uses 31 fewer steps than update four, a 3.7% reduction. Final task outcomes remain pending.

## Navigation continuation

The raw update-16 model also qualified on 14/16 development attempts and introduced new failures. A separate update-32 physical diagnosis failed sole clearance on a fixed-qualified reset. Remaining raw update-32 evaluation was stopped because that checkpoint cannot meet the monotone reliability gate. No full update-32 cohort result is reported.

The compact continuation retains direct and buffered control, uses shorter outcome-free planner summaries, and adds eight physically evaluated training layouts. The 32-layout corpus contains 26 direct and six buffered teacher choices. Sixteen further actual optimizer updates were completed from the saved update-32 state. All compact checkpoints, including parent zero and representation-control update 32, receive the same input contract.

Those sixteen updates have now completed. Compact checkpoint zero and the unchanged update-32 weights retain the earlier clearance failure. Update 40 matches the fixed profile's outcomes without reducing steps. Update 48 passes the development gate: 15/16 qualified attempts, no newly failed fixed successes, and 8.7% fewer mean paired-layout steps. It is frozen for the eight-layout final cohort. This is a development result, not yet a fresh-layout win.

Two duplicate development executions matched exactly in trajectories, controls, step events and balance samples. The compact development comparison uses those frozen physical action outcomes and labels this reuse explicitly. The training-fitted two-profile rule qualifies on 15/16 development attempts and uses 13.6% fewer mean paired-layout steps than the fixed strategy, with no new fixed-strategy failures. That is a conventional control result, not a trained-model result. Fresh navigation layouts were opened after checkpoint 48 was frozen; execution is in progress.

## Combined-model preflight

Task checkpoint eight was selected under fixed buffered navigation. Combining it with navigation checkpoint 48 completed all four tasks, without falls or forbidden contact, but missed laptop-leg median moving-sole clearance: 4.485 mm against the unchanged 4.5 mm requirement. The combined parent also completed all tasks but measured 4.311 mm on the drawer leg. Neither qualifies. Their 928 and 826 steps do not establish an efficiency improvement.

The final task layouts remain unopened. Extending the existing sole correction to station transits measured 4.064 mm on a reached-state laptop test and was rejected. A higher target reached 5.786 mm but timed out during pose capture. An intermediate target reached the station with 4.640 mm and no fall or forbidden contact. The full Modal development preflight is now testing that R5 revision under the same implementation for both frozen model sides. It retains the existing globe correction and leaves the navigation experiment, native gait and quality thresholds unchanged. These changes receive engineering credit, not training credit.

## Fresh navigation results

All sixteen parent, selected and training-selected fixed attempts now qualify across eight fresh layouts and two physics seeds, with no falls or forbidden contacts. Checkpoint 48 uses 16.0% fewer mean paired-layout steps and 14.2% less physical time than the fixed profile. Seven of eight layouts improve. The step-ratio layout bootstrap interval is 0.7855 to 0.8995. It passes the declared fixed-reference gate.

The earlier parent is stronger on this cohort: checkpoint 48 uses 9.7% more mean paired-layout steps and takes 8.7% more physical time than the parent. The parent always selected direct control; checkpoint 48 selected direct thirteen times and buffered three times. The additional training has not demonstrated an improvement over the earlier parent. The training-fitted contextual control also qualifies on 16/16 attempts. Checkpoint 48 uses 4.65% fewer mean paired-layout steps than that control, with a ratio interval of 0.8413 to 1.0878. This misses the five-percent gate and the interval includes parity. The complete comparison retains all four controls.

## Shared engineering, reported separately

The globe assembly was moved five centimetres east at reset. An east-facing approach and bounded, contact-gated sole feedback repaired the transition from the laptop. One development sequence qualified in 752 steps and 326.97 seconds. A different physics seed then fell during book descent. Slower support transfer passed matched descent probes without extra descent steps and qualified in a complete second-seed sequence. A separate furniture arrangement also qualified. These changes are controller engineering and receive zero Tinker training credit.

## Service evidence and limits

Exa retrieved failure-driven research for the training allocation. past.dev carried exact source-linked observations, hypotheses, plans and measured conclusions between distinct workflow identities. Reads waited for ingestion and verified the expected source ID; an unauthorized private-audience canary read was denied. These are actual shared-memory interactions. This campaign has not established a causal memory benefit.

Modal runs the fixed-source navigation experiments and authenticated training backend. Training data records distinguish local CPU from Modal and retain architecture. Final navigation comparisons use the same Modal runtime. Continuous task comparisons use matched local execution and keep full trajectories.

Original negative results and interrupted orchestration are preserved. A JSON scalar reporting error was repaired after all 32 navigation updates were saved. One interrupted artifact export was recovered from its complete authoritative raw episode without repeating physics or optimizer updates. Its missing function-end duration retains the conservative reservation. These repairs do not change outcomes or success thresholds.

Geometry is privileged. The robot does not infer the desk from cameras. This is a small state-based controller-selection study, with no hardware transfer claim, native gait training claim or robotics benchmark record.
