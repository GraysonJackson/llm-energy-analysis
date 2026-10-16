# Detailed implementation guide

This guide is the implementation specification for the expanded LLM Energy Analysis project. It describes the software to build, the experiments to run, the information to preserve, and the evidence needed before interpreting results.

Updated October 16, 2026. The code audit refers to repository commit e712d8d8ce7041b87d26f81542ec53fc0b41bc2c. A documentation commit does not imply the runtime corrections below have been implemented.

## Contents

1. [Scope and terminology](#1-scope-and-terminology)
2. [Existing code audit](#2-existing-code-audit)
3. [Implementation sequence](#3-implementation-sequence)
4. [Target architecture](#4-target-architecture)
5. [Configuration and planning](#5-configuration-and-planning)
6. [Records and data contracts](#6-records-and-data-contracts)
7. [Energy integration and timing](#7-energy-integration-and-timing)
8. [Meter adapter and collector](#8-meter-adapter-and-collector)
9. [Local inference implementation](#9-local-inference-implementation)
10. [Datasets and task evaluation](#10-datasets-and-task-evaluation)
11. [Experiment scheduling](#11-experiment-scheduling)
12. [Inference experiments](#12-inference-experiments)
13. [Cloud measurements and scenarios](#13-cloud-measurements-and-scenarios)
14. [Fine-tuning implementation](#14-fine-tuning-implementation)
15. [Training a small model from scratch](#15-training-a-small-model-from-scratch)
16. [Training-energy accounting](#16-training-energy-accounting)
17. [Analysis and uncertainty](#17-analysis-and-uncertainty)
18. [Reports and visualizations](#18-reports-and-visualizations)
19. [Validation and acceptance tests](#19-validation-and-acceptance-tests)
20. [Run procedures and recovery](#20-run-procedures-and-recovery)
21. [Milestones and handoff](#21-milestones-and-handoff)
22. [Sources and unresolved decisions](#22-sources-and-unresolved-decisions)

## 1 Scope and terminology

The central question is how model size, quantization, hardware configuration and task-specific training affect the energy required for useful local AI responses. Every experiment must produce an energy result and a task-quality result, or explicitly explain why one is unavailable.

Use the following terms consistently:

| Term | Meaning |
| --- | --- |
| Campaign | A versioned collection of related experiments |
| Run | One reproducible configuration/session with an immutable manifest |
| Condition | Model artifact, hardware, backend, settings and task suite being compared |
| Trial | One scheduled request attempt |
| Attempt | A particular execution, including retries; attempts are never overwritten |
| Session | A time block with a defined environment and baseline |
| Measurement window | Explicit interval integrated from wall-power samples |
| Gross energy | All workstation electricity in that interval |
| Incremental energy | Gross energy minus matched idle power times duration |
| Adequate response | An output passing the preregistered task-specific criteria |
| Training job | Setup, optimization, evaluation and saving for one model/seed |
| Inference | Generating outputs with an existing model |
| Fine-tuning | Updating a pretrained model or its adapters using task data |
| From-scratch training | Optimizing a randomly initialized small model |
| Cloud scenario | An assumed or sourced electricity estimate, not a provider power measurement |

Core work is valid local inference measurement. The original v1 suite is 20 prompts x two local models x two quantizations x three repetitions = 240 trials. The proposed four-domain v2 suite is 40 prompts x two models x two quantizations x three repetitions = 480 trials. Preserve their separate versions.

Fine-tuning pilots will cover coding, technical document questions, digital forensics and general questions. Larger models, longer contexts, full fine-tuning, multiple GPUs and from-scratch training are not an unrestricted Cartesian product. Promote feasible pilots to documented experiments.

A tiny from-scratch model and a large pretrained model have different data histories and capabilities. A result from one is not an equal-capability comparison with the other.

## 2 Existing code audit

Read the named functions before editing. The current defects are concrete implementation tasks, not merely stylistic changes.

| Priority | Location | Existing behavior | Target |
| --- | --- | --- | --- |
| P0 | src/local_llm_benchmark.py, benchmark_prompt | Starts/stops monitoring without continuous sampling | Collector runs across generation; validated trace exists |
| P0 | src/power_monitor.py, start_monitoring | Sets flags and resets a list only | Explicit collection lifecycle or clearly named session-only method |
| P0 | src/power_monitor.py, get_current_power | Assumes /status and legacy response shapes | Device-generation adapter and validated RPC response |
| P0 | LocalLLMBenchmark.count_tokens/generate | Estimates tokens with character length | Completion metadata and explicit token provenance |
| P0 | LocalLLMBenchmark.__init__ | Constructs a client without retaining it | Store client and use it for every method |
| P0 | LocalLLMBenchmark.generate | Timeout can stop a partial response then mark success | Completed/partial/timeout status and terminal metadata required |
| P0 | run_benchmark/run_baseline_measurement | Baseline collected once, not linked/subtracted | Baseline IDs and gross/incremental calculations |
| P0 | Local/cloud export_to_csv | Drops responses, errors and useful metadata | Lossless JSONL/raw references plus analysis CSV |
| P0 | CloudBenchmark._get_energy_per_token | Unsourced defaults, always applies PUE | Null when unknown; explicit source-bound scenario |
| P0 | CloudBenchmark cost methods | Historical combined token prices | Separate dated input/output/cache prices and actual usage |
| P0 | CloudBenchmark.test_connections | Hardcoded historical model IDs | Selected validated endpoint; health calls counted in budget |
| P0 | BenchmarkAnalyzer.load_latest_results | Independently chooses newest files | Explicit run IDs/manifests and compatibility checks |
| P0 | reports/generate_report.py | Discussion/conclusions can presume an energy premium | Evidence-driven conditional text with measurement labels |
| P1 | src/generate_graphs.py | Compares measured and estimated energy; assigns privacy 0/1 | Separate scenario styling and no invented privacy score |
| P1 | run_local_benchmarks/benchmark_model | Fixed ordering and pauses | Seeded blocked schedule, recorded thermal state, resume |
| P1 | config.yaml | Historical endpoints, implicit model tags, unsupported factors | Validated config with explicit artifacts and sources |
| P1 | src/analyze_results.py | Success-only summaries and ambiguous J/token | Failure accounting, quality filters and named denominators |
| P1 | src/dashboard.py | Independent monitor state and latest-file selection | Read-only view of the same run store |
| P1 | data/prompts.json | 20 legacy prompts, no ground-truth/split provenance | Immutable legacy suite plus separately versioned domain suite |
| P1 | requirements.txt | Broad minimum versions only | Tested inference lock and separate training environment |
| P2 | Training/evaluation modules | Absent | Dataset preparation, adaptation, scratch training and held-out scoring |
| P2 | Tests | No committed validation suite in audited tree | Fixtures for units, state, artifacts, budgets and failure modes |

Do not implement later research features on top of invalid power collection. P0 tasks precede publishable energy experiments.

The legacy API document also describes start_monitoring as a background-thread method, which the code does not implement. Its documented statistics names differ from actual return keys. Correct the reference when those interfaces are implemented.

## 3 Implementation sequence

### Phase A Make one trial trustworthy

1. Introduce manifest/trial/power records and an append-only run directory.
2. Implement device adapter detection and fixture tests.
3. Implement a collector with monotonic timestamps, request latency, error samples and clean shutdown.
4. Implement window integration and validity checks independently of a live device.
5. Fix the retained Ollama client, terminal metadata and completion states.
6. Run one synthetic workload, one short generation batch and one longer generation.
7. Recompute each energy value from the saved trace using a separate analysis function.
8. Freeze acceptance criteria and record the pilot outcome.

Exit condition: a complete output, actual token counts, bounded time window, bracketing power samples and a reproducible energy calculation. Without a meter, a run is functional-only and energy remains null.

### Phase B Run a reproducible inference campaign

1. Freeze model artifacts and the legacy prompt suite.
2. Record unloaded and loaded baselines.
3. Schedule seeded repeated blocks.
4. Persist every attempt and evaluate output adequacy.
5. Produce a run-level summary without cloud assumptions.
6. Re-run one selected condition in a separate session to inspect drift.

Exit condition: no unexplained missing trials; failure counts, energy, quality, hardware and environment are traceable.

### Phase C Expand domains and hardware comparisons

Build the four-domain dataset, validate scoring, run S2 and add one controlled extension at a time. Preserve the original suite as its own result set. Do not change the dataset while comparing conditions without starting a new campaign version.

### Phase D Add cloud comparison

Choose currently available endpoints, calculate cost from dated pricing and usage, enforce a request/spend budget, and keep server electricity as separately sourced scenarios. Local-only campaigns must continue to work without API credentials.

### Phase E Add adaptation

Validate PyTorch/ROCm training separately from Ollama. Pilot one domain first to prove the pipeline, then pilot all four domains. After feasibility review, select repeated seed/method comparisons. Save adapters, evaluate against the same base, and account for the whole campaign's training energy.

### Phase F Add small from-scratch study

Only after Phase A/B and a working training pilot. Select a feasible small model and fixed corpus/compute budget. Validate learnability, log curves and held-out metrics, and stop or scale according to measured memory/time.

### Phase G Final analysis and handoff

Freeze raw data, reproduce summaries, prepare plots/posters/report, document incomplete conditions and complete grant outputs within the approved period.

## 4 Target architecture

Preserve useful existing classes. Refactor small contracts rather than replacing the entire project at once. Suggested future layout:

~~~text
src/
  power_monitor.py          # meter adapters and collection lifecycle
  local_llm_benchmark.py    # Ollama backend
  cloud_benchmark.py        # provider backends, usage and cost
  run_benchmark.py          # orchestration and existing entry point
  records.py                # manifest/sample/trial validation
  energy.py                 # clipping, integration, baseline calculations
  planner.py                # matrix expansion, seeds and resumable schedule
  run_store.py              # append-only artifact writer and explicit lookup
  evaluation.py             # task validators and quality records
  datasets.py               # source-aware splits and version checks
  training/
    common.py               # seeds, device checks, callbacks and artifacts
    finetune.py             # LoRA/QLoRA jobs
    scratch.py              # small-model pretraining
  analyze_results.py        # explicit run analysis
  generate_graphs.py        # evidence-labeled figures
  dashboard.py              # read-only run observer
tests/
  fixtures/                 # tiny synthetic traces/responses/datasets
  test_energy.py
  test_meter_adapters.py
  test_local_backend.py
  test_planner.py
  test_run_store.py
  test_cloud_accounting.py
  test_dataset_splits.py
  test_evaluation.py
  test_training_contracts.py
~~~

These files are a proposed layout, not existing executable modules. Keep any future command documentation synchronized with implemented flags.

Component flow:

~~~text
validated configuration
  -> immutable manifest and schedule
  -> baseline/model preparation
  -> collector + selected inference/training backend
  -> immutable raw attempts, power samples and outputs
  -> measurement validation
  -> quality scoring
  -> explicit-run analysis
  -> report/figures
~~~

The dashboard observes the store. It must not reset, start or stop the active experiment's meter collector.

## 5 Configuration and planning

The example YAML under docs/examples is a planning contract. The current script does not parse its expanded schema. Implement parsing and validation before advertising new CLI options.

### Required config groups

| Group | Fields to implement |
| --- | --- |
| study | campaign ID, schema version, protocol version, root seed, public/private artifact policy |
| hardware | hardware ID, components, firmware, OS, device selection, power profile |
| meter | adapter kind, host/env reference, channel, poll target, timeouts, maximum valid gap, boundary policy |
| runtime | backend, host, version, device verification and timeout policy |
| models | exact ID, revision/digest, quantization, tokenizer, template, context and supported tasks |
| suite | dataset version/hash, split, prompt IDs, category mapping |
| generation | seed schedule, temperature, top-p, output cap, context cap, stop rules, reasoning mode |
| schedule | repetitions, sessions, block order, warm-up, cooldown/stability, baseline duration |
| cloud | disabled by default, endpoint IDs, pricing snapshot, spend/request caps, scenario sources |
| training | selected method, data/split hashes, base revision, precision, optimizer, step/token/time caps |
| output | private raw root, public summary root, checkpoint policy, resume policy |

Reject missing required model revisions or duplicate IDs. Reject output caps larger than selected context limits. Reject generation settings unsupported by a backend instead of silently dropping them.

Treat null as unavailable and zero as a measured/configured zero. A missing meter cannot become 0 joules; an unknown price cannot become $0; a missing validation score cannot become a passing score.

### Preflight without generation

The planned preflight must:

1. Validate syntax, schema and path existence.
2. Verify model availability and exact artifact metadata without implicitly downloading unbounded weights.
3. Calculate intended trial count and per-condition counts.
4. Print train/validation/test sizes and leakage checks.
5. Estimate disk and worst-case cloud spend with documented assumptions.
6. Verify device/backend and current free memory.
7. Check that budget and wall-time caps are positive where applicable.
8. Produce an immutable schedule file before any paid/long job begins.
9. Require a separate explicit launch action after the dry run.

Health probes that generate responses are real usage and must appear in the campaign budget.

## 6 Records and data contracts

Use UTC RFC3339 timestamps for human correlation and monotonic nanoseconds for intervals. Store schema_version and units explicitly.

### Run manifest

Required fields:

- run_id, campaign_id, protocol_version, schema_version and created_at_utc.
- git_commit, working_tree_dirty, resolved_config_hash, resolved_config_path.
- hardware_id, hardware inventory hash and software/environment lock hash.
- OS, kernel, Python, runtime, GPU driver, ROCm/PyTorch where relevant.
- Model IDs/revisions/digests, tokenizers, templates, quantizations and device placement.
- Dataset version, source manifest, split hashes, prompt-list hash.
- Root/randomization/training/generation seeds and determinism flags.
- Meter identity/firmware/adapter, measurement boundary and uncertainty notes.
- Planned conditions/trial counts, attempt policy, expense/time limits.
- Parent/resumed run references, operator notes and run status.
- Source snapshots used for API pricing and cloud scenarios.

Do not publish IPs, API keys, account IDs, serial numbers or private paths in a public manifest. Keep a sanitized public export with provenance hashes.

### Power sample

| Field | Type/meaning |
| --- | --- |
| sample_id | Unique immutable ID |
| run_id, collector_id | Link to one collector and run |
| request_sent_mono_ns | Meter HTTP send time |
| response_received_mono_ns | Receive time |
| sample_mono_ns | Chosen host timestamp, normally midpoint |
| timestamp_utc | Correlation timestamp |
| device_timestamp | Optional device time with provenance |
| power_w | Number or null |
| cumulative_energy_wh | Optional reported meter counter |
| voltage_v, current_a | Optional diagnostics |
| meter_update_id | Optional source sequence/update timestamp |
| status | ok, timeout, parse_error, nonfinite, device_error |
| error_code, payload_ref | Sanitized error and private raw reference |

Repeated unchanged power values can be real; do not deduplicate them by value. If a device timestamp exposes stale updates, mark staleness based on that information.

### Trial record

Required identity: trial_id, attempt_id, run_id, session_id, block_id, condition_id, prompt_id, suite_version and repetition.

Required configuration: model_artifact_id, backend, quantization, context_limit, output_limit, actual generation settings, seeds, cold/warm/cache policy and placement evidence.

Required observation:

- request_start/end monotonic times and UTC timestamps.
- first_nonempty_response_time where available.
- input/output/total tokens, token source, completion/stop reason.
- client wall duration and separate runtime loading/prefill/decode durations where provided.
- response_ref, response hash, sanitized error_ref.
- baseline_id, power_trace_ref, measurement window and sample counts.
- gross J, incremental J, time-weighted mean W, energy validity and exclusion reasons.
- quality_record_ref and quality validity.
- local/cloud classification, cost provenance and scenario references.
- statuses for execution, measurement and quality separately.

Suggested execution states: completed, truncated, timeout, cancelled, backend_error, out_of_memory. Measurement states: valid, missing_meter, insufficient_samples, missing_boundary, sample_gap, invalid_power, clock_error. Quality states: unscored, adequate, inadequate, not_applicable.

A record can be completed but measurement-invalid or quality-inadequate. Avoid one success boolean trying to express all three.

### Training record

Include job_id, domain, base revision or scratch architecture, dataset/split/tokenizer hashes, method, adapter configuration, precision, optimizer, batch size, gradient accumulation, learning rate, scheduler, seed, step/token/epoch caps and actual counts.

Include setup/optimization/validation/save windows, gross/incremental energy for nonoverlapping phases, total job/campaign energy, peaks of VRAM/RAM, wall time, checkpoint IDs, stopping reason and validation metrics.

### Artifact directory

~~~text
runs/<run_id>/
  manifest.json
  resolved_config.yaml
  schedule.jsonl
  events.jsonl
  baselines.jsonl
  power/samples.jsonl
  trials/attempts.jsonl
  responses/<attempt_id>.json
  quality/scores.jsonl
  training/jobs.jsonl
  artifacts/checkpoints/...
  analysis/summary.json
  analysis/exclusions.csv
  analysis/figures/...
  checksums.sha256
~~~

Keep full text and raw traces private initially. Derived CSV is an export, not the only source of truth. Write metadata atomically; append records with flush/checkpoint policy and recover a partial final JSONL line visibly.

## 7 Energy integration and timing

### Clock policy

Use one host monotonic clock for collection and workload timestamps when possible. Do not integrate wall-clock timestamps that can jump. Record UTC for correlation only. A remote collector requires explicit synchronization and a measured bound on clock offset/drift; same-machine collection is the primary design.

An HTTP midpoint is an estimate of observation time, not proof that the meter measured then. Record round-trip latency and device update behavior. Polling faster does not necessarily improve meter resolution.

### Boundary handling

Keep a continuous collector alive long enough to obtain one accepted sample before request_start and one after request_end. Clip integration to the exact chosen interval. Interpolate power at the edges only when both neighboring samples are valid and their gap passes policy.

If the boundary cannot be bracketed, mark energy invalid. Do not replace the unknown beginning/end with zero power or extend the last reading without a declared method.

### Calculations

~~~text
E_gross_J = sum(0.5 * (P_i + P_i_plus_1) * delta_t_seconds)
duration_s = (end_mono_ns - start_mono_ns) / 1e9
P_time_weighted_W = E_gross_J / duration_s
E_incremental_J = E_gross_J - idle_mean_W * duration_s
Wh = J / 3600
kWh = J / 3_600_000
J_per_output_token = E_gross_J / reported_output_tokens
~~~

Only divide when the denominator is positive. Keep optional total-token normalization under a different field. Unweighted sample-average W is a diagnostic and can differ from the time-weighted average with irregular sampling.

Preserve negative incremental energy and flag it for baseline/uncertainty review. Never silently clamp it. Gross power integration should not be negative for an ordinary consuming workstation; inspect device sign conventions.

### Gap and sample policy

Start the pilot with approximately one-second requested polling. Select the accepted maximum gap after characterizing the meter. A possible pilot candidate is twice the nominal interval, but it is not an established device specification.

Record valid coverage fraction, largest gap, actual update interval, valid/error counts and boundary status. A missing interval invalidates the primary energy result under a strict policy. A sensitivity reconstruction may be published separately with its interpolation assumptions, never merged into directly observed results.

For very short requests, use repeated batches in a longer measured window. Keep batch size, all outputs and timing. Dividing batch energy by count gives an amortized average and includes inter-request overhead; it is not a resolved per-request power trace.

### Baselines

Measure no-model idle and model-loaded idle separately. Use at least 60 seconds for a relevant baseline; extend when the trace is unstable. Capture pre/post block baselines and retain their variation.

Link each trial to a baseline representing its actual state. Do not subtract OS-only idle from a loaded-model steady-state interval without labeling that choice. Record reference duration and uncertainty. If pre/post baselines drift materially under the chosen pilot threshold, inspect or repeat the block.

### Deterministic numeric fixtures

Implement the following tests without a live meter:

| Fixture | Expected |
| --- | --- |
| Constant 200W for 5s | 1000J, 0.277777...Wh |
| Linear ramp 100W to 300W over 10s | 2000J |
| 1000J over 5s with idle 100W | 500J incremental |
| 500J, 100 output tokens | 5J/output token |
| 500J, 0 output tokens | Null token-normalized energy, not zero |
| 1kWh | 3,600,000J |
| 0.001kWh per 1,000 tokens | 3.6J/token before any justified overhead |
| Samples around a clipped partial interval | Integrate interpolated edges exactly |
| Duplicate timestamps, reversed time or NaN | Rejected/flagged according to documented policy |
| Long missing interval | Invalid primary energy |
| Gross below estimated idle subtraction | Negative incremental retained and flagged |

These are validation fixtures, not measured results.

## 8 Meter adapter and collector

### Adapter contract

Implement methods equivalent to:

~~~python
class MeterAdapter:
    def identify(self): ...
    def read_sample(self): ...
    def capabilities(self): ...
~~~

identify returns model, firmware, supported channel/API and sanitized identity. read_sample returns a typed sample or typed failure. capabilities declares whether cumulative Wh, voltage, current and device timestamps are actually available.

For Gen1 validate the actual /status shape. For Gen2+ candidates verify the selected firmware's RPC endpoint, commonly /rpc/Switch.GetStatus?id=0, and apower. Do not infer that a product name guarantees the same endpoint or that every Switch has power metering.

Use read-only polling. Avoid relay-control or counter-reset calls in the benchmark. Meter authentication is a local secret; never log Authorization headers.

### Collector lifecycle

Suggested states: stopped -> starting -> ready -> collecting -> draining -> stopped, with failed as a visible terminal state.

- A single thread/process owns meter polling and sample ordering.
- Keep a stop event, readiness event, finite HTTP timeout and bounded join policy.
- Take an initial sample before readiness.
- Schedule next deadlines on a monotonic clock rather than sleeping a fixed interval after slow requests.
- On a slow poll, record the missed target/deadline; do not burst simultaneous compensating polls.
- Capture exceptions as events and attempt a documented bounded recovery.
- Workload success cannot hide a failed collector.
- Shutdown obtains a final bracketing sample when possible, flushes records and joins the collector.
- If join fails, mark the run incomplete and prevent a second collector from taking ownership unnoticed.

### Trial lifecycle pseudocode

~~~python
collector.start()
collector.wait_until_ready(timeout=ready_timeout)
try:
    baseline = measure_relevant_idle_state()
    collector.wait_for_valid_sample()
    start = monotonic_ns()
    result = backend.generate(request)
    end = monotonic_ns()
    collector.wait_for_sample_after(end)
finally:
    collector.stop_and_flush()

trial = persist_attempt(result, start, end)
measurement = integrate_and_validate(trace, start, end, baseline)
persist_measurement(trial.id, measurement)
~~~

Production code must initialize result/start/end safely and retain partial artifacts on exceptions. The pseudocode describes control flow, not a ready-to-run implementation.

For a campaign, prefer one collector across baseline and trial blocks so boundaries are easier to preserve. Mark separate windows in that trace rather than repeatedly resetting a shared list.

### Physical validation

1. Confirm exact plug, rating, firmware and correct channel.
2. Verify no unrelated devices share the metered load.
3. Compare stable idle and a longer repeatable computer load.
4. Check cumulative Wh against integrated samples over a sufficiently long interval if available.
5. Repeat at different load levels and document offsets/resolution.
6. If a reference meter is available, compare and record its own uncertainty.
7. Document polling overhead by running a comparable workload with the same collection settings.
8. Report limitations honestly. Resolution, repeatability and calibration accuracy are different properties.

## 9 Local inference implementation

### Client and artifact identity

Retain a configured ollama.Client as self.client. Use it for list/show/generate operations. Validate the installed SDK's actual response object interface; do not assume every version returns an identical dictionary.

Pin and record model name/tag, digest, architecture/parameter count, weight quantization, tokenizer and prompt template. Tags can change. Save model metadata in the manifest. Verify requested context length and runtime options are effective.

### Completion and timing

For streaming:

1. Record client request start.
2. Preserve chunks privately if needed for diagnostics.
3. Mark first response only when actual nonempty content arrives.
4. Distinguish reasoning text from displayed answer if the model exposes both.
5. Continue until an explicit terminal response or a failure.
6. Capture terminal token/duration metadata.
7. Record completion/stop reason, including output limit.
8. Close/cancel the stream on timeout; do not leave backend work running into the next baseline.
9. Verify backend/device quiescence before the next block.

Ollama reports prompt_eval_count, eval_count and duration fields. Use these instead of len(text)//4 or stream-chunk counts. Convert nanosecond durations to seconds. Preserve cached-prompt counts where available and document whether reported input counts include cached tokens.

A timeout with partial output is not completed. A limit-ended answer may be adequate or inadequate according to the rubric, but remains tagged truncated/limit-ended.

### Metric definitions

- Client latency: request send to final response receipt.
- First-response latency: request send to first nonempty answer chunk.
- Runtime decode speed: reported output tokens divided by reported decode seconds.
- End-to-end output speed: output tokens divided by client wall seconds.
- Energy: wall-power integration over the defined request window.
- Quality: independent held-out scoring.

Do not call client latency GPU-only generation time. An unstreamed endpoint cannot provide observed first-token latency; use null rather than zero.

### Device placement and warm-up

Confirm placement through Ollama process metadata and system telemetry. Check that R9700 trials actually use the selected discrete GPU rather than the 5600G integrated GPU or CPU fallback. Capture actual offload state when available.

Warm-up should include representative prefill and generation, not only the legacy ten-token ready response. Record but exclude warm-up from steady-state trial averages. A model can unload during a long cooldown; verify residency or intentionally designate a cold trial.

Restarting the runtime, changing firmware or drivers, switching OS, or adjusting power profiles begins a new condition/session. Preserve logs.

## 10 Datasets and task evaluation

Detailed domain definitions are in datasets_and_evaluation.md. Implement:

1. Source manifest with license, retrieval date, source/group ID and content hash.
2. Normalization that preserves meaningful code/log formatting.
3. Exact and near-duplicate detection.
4. Source-group train/validation/test split before creating derivative examples.
5. Immutable prompt/answer/scoring records.
6. Frozen evaluation suite with a separate version from training data.
7. Training-only fitting of preprocessing, retrieval indexes or vocabulary decisions where applicable.
8. Audit report with counts by source/domain/split and exclusion reasons.

For coding, run generated code in a disposable restricted environment without credentials/network access. A Python subprocess timeout alone is not a security boundary. Score tests using independently reviewed assertions and preserve test results.

For document questions, require evidence from supplied passages, include answerable/unanswerable questions and test invented citations. Keep source documents out of the training split when they are held out for evaluation.

For forensics, use authored synthetic artifacts with known ground truth. Evaluate event ordering, hash interpretation, evidence attribution and explicit uncertainty. No real case records or personal logs are needed.

For general questions, use verifiable answers and bounded reasoning. Preserve ambiguity notes and avoid unverifiable current-news questions unless dated sources are frozen.

### Scoring contract

Record task rubric version, evaluator/version, item scores, adequate boolean, explanations, evidence references and review status. Do not ask a model to score its own answers without an independent check.

A proposed 0-2 rubric can cover correctness, requested completeness, groundedness/evidence and uncertainty handling. Set adequacy thresholds before main data collection. Coding unit-test pass rate is separate from prose rubric scores. Keep domain-level results rather than treating all scores as identical units.

For a small solo study, blind model/condition labels during manual review where practical. Re-score a sample later and ask the mentor to review a subset. Report disagreement and unresolved items.

Avoid API-judge evaluation by default: it adds expense, data movement and another model bias. If used, record evaluator, prompts, usage, consistency checks and energy/cost boundary separately.

## 11 Experiment scheduling

Use docs/experiment_matrix.csv as a planning inventory. Counts are explicit targets, not implemented schedules or completed measurements.

### Pilot ladder

- Functional smoke: two tasks per domain, one small model/quantization, two repeats = 16 request attempts.
- Meter pilot: stable idle, longer known load and repeated generation batches.
- Original core: 20 x 2 x 2 x 3 = 240 trials.
- Expanded four-domain suite: 40 x 2 x 2 x 3 = 480 trials.
- Cloud expanded comparison: up to 40 x 2 endpoints x 3 = 240 requests, only after estimating spend.
- Larger-model diagnostic: ten selected prompts x two feasible quantizations x three repetitions = up to 60 trials per selected larger model.

Use the same selected prompts across compared conditions. If a larger model cannot run a quantization/context, retain the infeasible condition in the matrix and compare only valid matched subsets.

### Blocking and randomization

Randomize prompt order and condition block order using a saved root seed and generated schedule. Keep model loading outside warm windows. Avoid switching models on every request solely to randomize if it changes the loading-energy boundary; randomized blocks are acceptable.

Distribute repetitions across independent sessions. Schedule enough matched prompts in every session to estimate drift. Store sequence indices and actual start/end times.

A retry receives a new attempt ID pointing to the original trial. Record failed energy/cost. Resume only missing approved attempts; never replace a failed record with a successful retry invisibly.

### Size the campaign before launching

Estimate total device time:

~~~text
planned_seconds =
  baseline_seconds + load_warmup_seconds
  + sum(expected_trial_seconds + intertrial_overhead)
  + training_seconds + validation_save_seconds
~~~

Treat expected times as pilot estimates with uncertainty. Set total cloud spend, maximum training job hours, storage cap and experiment completion cutoff. Stop launching optional work early enough to analyze/write before the grant end.

## 12 Inference experiments

### E1 Original baseline and quantization

Question: what changes when quantization changes for the same model?

- Two existing candidate families: Llama 3 8B and Mistral 7B, subject to exact obtainable artifacts and license/support checks.
- Two documented weight quantizations where available, such as Q4 and Q8 variants of the same base revision.
- Same prompt suite, template, requested output cap and context cap.
- Record effective precision/backend and actual memory use.
- Compare paired energy/request, output tokens, quality, latency and token-normalized diagnostics.
- Do not compare different model revisions and attribute the effect solely to quantization.

Exit: valid traces and quality records for the selected 240-trial core, or an explicit report of unavailable conditions.

### E2 Four-domain benchmark

Build ten evaluation tasks per domain for an initial 40-item suite. Balance easy/moderate/hard and answerable/unanswerable items where appropriate. Run the two-model/two-quantization/three-repeat design only after pilot validation.

Report each domain separately and the weighting used for any combined metric. Ten tasks per domain provide an initial small study, not broad certification of forensic or coding capability.

### E3 Larger-model capacity

Investigate candidate sizes above the core models, for example roughly 14B and 30-32B quantized models if artifacts/runtime and memory allow. These are inference candidates, not a promise that training of the same sizes fits.

- Select comparable family revisions when possible.
- Estimate weights plus KV cache plus runtime overhead before download/load.
- Test a short context first, then increase deliberately.
- Record load failure, peak allocated/resident memory, offloading and decode speed.
- Separate GPU-resident from mixed CPU/GPU conditions.
- Keep a diagnostic set common to smaller models.
- Record OOM conditions and memory peaks rather than hiding them.

Model parameter count is only one factor; architecture, active parameters, tokenizer, quantization and runtime can differ.

### E4 Context and output lengths

Proposed pilot context targets: 512, 2048 and 4096 tokens, using fixed source material and a controlled requested answer length. Verify actual token counts per tokenizer. Keep real task content and difficulty comparable.

Study context and output cap separately. Increasing both at once cannot identify their individual effects. Include prompt caching as an explicit setting and label any repeated-prefix cache advantage.

For generation length studies, compare requested caps and actual completion/quality. Shorter incomplete responses are not automatically more efficient.

### E5 CPU-only and partial offloading

Choose a model that fits existing system RAM. Verify device placement and log offload configuration. Compare the same artifact/backend if supported. If changing backend, report a backend-plus-placement comparison.

Measure whole-system energy, peak RAM, wall latency and quality. A faster CPU may improve preparation/offload behavior; do not assume it speeds fully GPU-bound decoding proportionally.

### E6 Hardware upgrade comparison

Where practical preserve data from:
- H0: existing CPU/GPU.
- H1: upgraded CPU/PSU with existing GPU.
- H2: upgraded CPU/PSU with R9700.

Do not reinstall parts just to fill this matrix if impractical. If only H0/H2 exist, label a complete-system comparison. Record OS/driver/backend changes. A PSU change also changes wall losses and is part of that boundary.

### E7 Cold/warm and idle behavior

Measure model-unloaded idle, loaded idle, cold load plus inference, warm inference and a defined ready/idle usage scenario. Count cold loading only in the appropriate condition.

For a usage scenario:

~~~text
daily_energy =
  sum(request_energy)
  + explicitly modeled ready_idle_energy
  + startup_loading_energy
~~~

Avoid counting idle time both inside measured request energy and again as a full-day idle baseline.

### E8 Optional power-profile study

Only after stable default measurements, compare a supported documented power profile/limit. Record actual setting, observed power, stability and output quality. Keep the default control. Do not equate a lower wattage with lower joules: total runtime matters.

### E9 Optional concurrency

Current primary design is one request at a time. A later explicit concurrency study may test one versus two/three simultaneous requests using the same total workload. Measure a whole batch, throughput, queue delay and all outputs. Allocation of batch electricity to requests is a modeled attribution, not a separate meter measurement per request.

No multi-GPU or concurrent-serving requirement is implied by the current one-card plan.

## 13 Cloud measurements and scenarios

### Provider backend

Select currently available endpoints at execution time and record provider model identifier/revision, endpoint/API, region if known, request settings, SDK version, system prompt and any reasoning settings.

Use the same task content and answer constraints, acknowledging tokenization/template differences. Preserve usage, response, completion reason, latency, retry events and actual billed amount where obtainable.

Health probes, retries, failed-but-billed requests, evaluator calls and training-data generation requests count toward the API budget. Disable automatic unlimited retries. Never submit private case records.

### Price model

Store a dated pricing snapshot with URL and currency. Calculate applicable components separately:

~~~text
cost_usd =
  uncached_input_tokens / pricing_unit * input_rate
  + cached_input_tokens / pricing_unit * cached_input_rate
  + billed_output_tokens / pricing_unit * output_rate
  + other_explicit_fees
~~~

Use actual provider semantics for cached and reasoning tokens. Do not subtract cache counts twice or assume displayed text equals billed output. If a rate is missing, keep estimated cost unavailable and enforce a conservative cap before running.

Maintain a spend ledger across process restarts. Reserve worst-case remaining cost before a request so concurrent workers cannot all spend the same remaining budget. The planned $200 API allocation is a planning cap, not a token guarantee.

### Energy provenance

Each scenario record needs scenario_id, source URL/title/date, model/workload context, original units, input/output treatment, hardware/system boundary, PUE inclusion flag and uncertainty/range.

Support source-bound input/output factors when justified. A generic fixed J/token is a sensitivity assumption and must be labeled as such. Unknown energy is null, not the legacy default 3.0J/token.

Check units explicitly:

~~~text
J_per_token_from_kWh_per_1000_tokens =
  value * 3_600_000 / 1000
~~~

Only apply PUE to IT-only energy that excludes facilities. Do not multiply an already whole-facility estimate again. Network/client energy is another boundary and is not silently added or omitted.

Cloud/local energy ratios are scenario-dependent and do not establish a causal privacy cost. When comparable evidence is unavailable, publish measured local results plus cloud latency/cost only.

## 14 Fine-tuning implementation

### Feasibility before promise

Validate the exact GPU, OS, ROCm, PyTorch, attention kernels, tokenizer, PEFT and optional quantization package combination. R9700 support in Ollama does not establish that a CUDA-focused QLoRA example works on AMD.

Use a separate environment/container from baseline inference. Pin the image/package versions and record a digest/lock after the smoke test. On ROCm, some PyTorch device interfaces retain CUDA naming; inspect actual HIP/backend/device identity rather than assuming those names imply NVIDIA hardware.

Test a single forward/backward/optimizer step before a long run. Confirm parameters update, loss is finite, artifacts save/load, and the intended device executes work.

### Data and base selection

Choose one modest pretrained base whose license permits adaptation and whose memory use passes the pilot. Freeze exact revision, tokenizer and chat template. Start with a manageable model, potentially in the 3B-8B range depending on the validated method. This is a candidate range, not a fit guarantee.

Prepare four separate domain datasets and one shared held-out evaluation protocol. Keep a general-domain regression set for each adapter. Do not train on evaluation prompts, answers or their paraphrases.

A proposed pilot size is 100-300 carefully checked examples per domain. Increase only when quality, data rights and device time support it. These counts are planning choices, not a claim of statistical sufficiency.

### LoRA first

Explicitly configure:
- adapter rank and alpha.
- target modules resolved against the actual architecture.
- dropout and bias policy.
- base weight precision and trainable parameter count.
- optimizer, learning rate and schedule.
- microbatch, accumulation and effective batch.
- sequence length, packing/truncation and loss mask.
- maximum steps, epochs, total tokens and job wall time.
- evaluation/save intervals and early stopping.
- seed and deterministic-operation policy.

Pilot candidate ranks 8 and 16 and sequence caps 512/1024 can be explored one factor at a time. A learning rate must be selected through a small documented validation pilot rather than asserted as universally correct.

Verify that only intended parameters require gradients. For instruction data, explicitly define whether loss applies only to the answer or the entire conversation. Padding tokens must not silently contribute to loss.

Keep effective batch size constant when comparing methods unless batch size itself is the factor. Log actual nonpadding tokens and optimizer steps.

### QLoRA as a separate condition

Validate quantized loading, optimizer and backward kernels on the exact AMD environment. Record quantization scheme, compute dtype, double-quantization or equivalent choices, backend/package and any fallback.

If unsupported or unstable, retain the failure/limitation and proceed with a validated LoRA path. Do not switch to a different method while labeling the output QLoRA.

### Four-domain pilot design

1. Validate one domain end to end.
2. Run one bounded pilot job for each of the four domains.
3. Compare held-out quality against the same base.
4. Check general-domain regression, training energy and inference behavior.
5. Review with mentor before promoting larger runs.

For the selected full comparison, target three independent training seeds per domain when compute permits. One base x four adapters/domains x three seeds = 12 jobs for one method. Adding a second method doubles that training count. Every adaptation still needs its own evaluation requests and energy.

Report seed variability. Three inference repeats on one trained adapter do not equal three independent training seeds.

### Save, reload and evaluate

Persist adapter config/weights, base/tokenizer revisions, source hashes and training metadata. Validate reloading from a clean process. If converting/merging for Ollama, verify supported conversion path and equivalence on a fixed diagnostic set.

Separate evaluation of the original training-runtime artifact from the deployed/quantized artifact. Conversion or additional quantization can change quality and energy. Do not attribute those changes only to fine-tuning.

Do not promise direct adapter import into a particular runtime until supported format and architecture have been checked.

### Report useful findings

Possible outcomes include improved quality at unchanged inference energy, a smaller adapted model matching a larger model on a narrow task, no meaningful improvement, worse generalization, or an infeasible configuration. Preserve them all.

## 15 Training a small model from scratch

This extension tests the complete training pipeline at small scale. It does not aim to reproduce commercial-scale LLM pretraining.

### Model and corpus pilot

Select a small decoder-only architecture after estimating weight, gradient, optimizer and activation memory. Candidate pilot scales are tens of millions of parameters. Record layers, hidden size, heads, vocabulary, positional encoding, context limit and parameter count.

Use a public/appropriately licensed or authored corpus. Freeze train/validation/test source groups before tokenizer fitting. If comparing tokenizers, the same text and compute/token budget need explicit interpretation because token counts change.

Record corpus bytes, unique documents, unique tokens, token repetition over epochs and domain proportions. A synthetic corpus can test learning but does not support broad language-capability claims.

### Implementation procedure

1. Instantiate random weights with recorded initialization and seed.
2. Verify parameter count and a forward/backward pass.
3. Overfit a tiny training-only fixture to prove the optimization pipeline can learn.
4. Confirm loss masking and next-token label shifting are correct.
5. Establish a held-out loss baseline before training.
6. Train under a fixed step/token/time cap.
7. Log train/validation loss, learning rate, token throughput, memory and energy.
8. Checkpoint periodically and test a resume.
9. Evaluate frozen held-out tasks and save failure examples.
10. Reproduce a selected small configuration with another seed if feasible.

A tiny-fixture overfit test is debugging evidence, not generalization evidence.

### Comparison policy

Use same-architecture random-initialization comparisons when studying data or compute changes. Compare task usefulness with pretrained systems as contextual information while acknowledging their different scale, pretraining and tokenizers.

Perplexity is comparable only under the same tokenizer, evaluation text, loss mask and normalization. Do not compare raw perplexities across unrelated tokenizers as if they share a scale.

Set a stop rule for nonfinite loss, sustained no improvement, OOM, temperature/device instability, job time cap or approaching report deadline. Retain failed-job energy.

## 16 Training-energy accounting

Define nonoverlapping windows:
- model/data loading and preparation.
- optimization steps.
- validation.
- checkpoint saving.
- conversion/export.
- subsequent held-out inference.

GPU work can be asynchronous. Record host phase timing and use the appropriate backend synchronization when establishing a boundary, without adding synchronization to every step unless it is part of the controlled protocol. Meter temporal resolution limits step-level power attribution; prefer long windows or groups of steps.

Record:
- total gross/incremental training-job energy.
- campaign energy including pilot searches and failed runs.
- actual training tokens, optimizer steps and wall time.
- J/training token and J/optimizer step as clearly bounded diagnostics.
- evaluation and checkpoint overhead.
- peak VRAM/RAM and observed throughput.
- quality gain and regression versus unchanged base.

Do not add phase energies twice when they already belong to the total job window.

### Adaptation amortization

If an adapted model yields lower energy per equally adequate request, estimate:

~~~text
N_break_even =
  additional_training_energy_J
  / (baseline_energy_per_request_J - adapted_energy_per_request_J)
~~~

Only calculate a positive finite threshold when the denominator is positive, boundaries match and quality is comparable. Otherwise report no energy break-even under the tested assumptions.

Show a successful-job-only threshold and an all-development-campaign threshold separately. Include deployment conversion and usage scenarios explicitly. A training run consuming energy does not mean future savings will occur.

If comparing a small adapted model with a larger base, report the model-size change as part of the intervention. Use a fixed adequate-task mix rather than cherry-picking only tasks improved by adaptation.

## 17 Analysis and uncertainty

### Data selection

Analysis takes explicit run IDs, protocol versions and allowed condition IDs. It verifies manifest/config/dataset/model compatibility. Legacy CSV is imported under a declared legacy schema with limitations; it is not silently upgraded to validated energy.

Preserve all planned trials and attempts. Export counts for scheduled, completed, truncated, failed, measurement-valid, scored and adequate. Publish exclusion reasons and energy/cost of failed attempts.

### Primary summaries

For each domain and condition report:
- number of distinct prompts/source groups/sessions.
- attempted and adequate response counts.
- mean/median gross J/request and incremental J/request.
- latency and throughput distributions.
- quality score and adequacy fraction.
- total campaign electricity and cost where applicable.
- output length and truncation rate.
- peak memory and offloading state.

Report energy per adequate response with a declared definition. A useful operational metric is total attempted energy divided by number of adequate outputs, which includes failures in the numerator. This becomes unavailable/infinite when no response is adequate; do not hide it as zero.

### Paired comparisons

Match prompt/source, condition and session where possible. Average or model repeated attempts per prompt before treating prompts as independent evidence. Use paired differences and effect sizes.

Bootstrap at an appropriate independent cluster, such as prompt or source document, retaining within-cluster repetitions. Report interval method and sample size. Do not claim significance from three repeated executions of a single prompt.

Different task difficulty, tokenizers, stop behavior and answer quality can explain apparent efficiency differences. Stratify rather than pool blindly.

### Meter uncertainty and sensitivity

Separate sampling gaps, polling latency, device accuracy, baseline drift, thermal variation and run-to-run noise. Do not claim sample variance covers meter calibration uncertainty.

Repeat analyses under defensible baseline/scenario choices. If differences are comparable to measurement uncertainty, report them as unresolved. Raw high precision in CSV is not measurement accuracy.

For cloud scenarios show how conclusions change across source ranges and boundaries. Do not use unverified factors to claim environmental superiority.

### Electricity and carbon

Primary result units are J, Wh and kWh. Electricity cost needs a dated tariff and usage scenario. GPU or API purchase costs are different from electricity cost.

Operational carbon is optional only with a location/time-specific intensity source and consistent units. Embodied hardware, water, facility construction and lifecycle impact are outside the primary study unless a separate scoped method is added.

## 18 Reports and visualizations

Refactor current report/graph code after record contracts stabilize. It must not generate a predetermined conclusion.

Required outputs:
1. Run inventory and trial-accounting table.
2. Local measured energy versus task quality by condition/domain.
3. Paired quantization and model-size comparisons.
4. Labeled power traces showing baselines, request and collection gaps.
5. Latency, token length, memory and adequacy summaries.
6. Training-energy and learning-curve figures for completed extensions.
7. Adaptation base-versus-adapter and general-domain regression results.
8. Separate cloud latency/cost and energy-scenario plots where justified.
9. Failure/infeasibility table, not just successful measurements.
10. Assumptions, uncertainty and scope limitations.

Figure captions identify gross/incremental boundary, cold/warm, units, independent n, error-bar meaning, exact suite and measured versus estimated values.

Remove the privacy 0/1 scatter plot. Use a deployment-description table for data movement/control. Local hosting can keep processing local while downloads, telemetry, APIs or retrieval may still involve a network.

Report text must be conditional on actual results. No-results runs produce a status report, not findings. Unknown cloud energy produces a missing-evidence section, not a default ratio.

Cite exact source URLs/dates in the report. Save analysis config, software versions and figure-generation command with the run.

## 19 Validation and acceptance tests

Tests are requirements for later implementation. This documentation commit does not add a fake passing suite or run the hardware experiments.

### Energy tests

Implement all numeric fixtures in section 7 plus:
- nonuniform sampling and clipped boundaries.
- cumulative Wh reset/rollover/error handling if that feature is used.
- insufficient coverage and large-gap rejection.
- time-weighted power versus unweighted samples.
- no division by zero and null propagation.
- no negative-energy clamping.
- meter error not converted into zero load.

### Meter/collector tests

Mock responses for actual adapter generations and authentication failures. Test timeout, malformed JSON, missing apower, null/nonfinite/negative values, stale device timestamp and transport errors.

Verify start/ready/stop ordering, finite thread join, exceptions during workload, final flush, no samples after ownership ends and no second collector accidentally sharing mutable state.

### Inference tests

Use recorded synthetic stream fixtures, not paid APIs:
- terminal metadata gives correct input/output counts.
- empty/control chunks do not create first-token latency.
- timeout retains partial output and noncompleted status.
- configured host is used by every client method.
- explicit model digest and options preserved.
- backend-reported limit ending remains identifiable.
- absent first-token timing stays null.
- missing GPU evidence cannot be labeled verified GPU execution.

### Planner/store tests

Verify exact counts for core/expanded matrices and reproducibility of a seed. Different seeds may change order but not required condition counts.

Resume must not duplicate completed attempts, overwrite failures or combine incompatible datasets. Corrupted final JSONL line triggers recovery evidence. Unique IDs, atomic manifest writing, config hashes and schema versions must be checked.

### Cloud tests

No network access in routine unit tests. Use synthetic usage/rate fixtures for input/output/cache/reasoning semantics, unknown prices, zero tokens, currency, hard caps, retries and restart-safe ledgers.

Verify kWh/1,000-token conversion and no double PUE. Unknown scenarios remain null. A health probe is counted.

### Dataset/evaluation tests

- Source-family splits are disjoint.
- Exact/near duplicates and derivative documents cannot cross splits unnoticed.
- IDs and source hashes are stable.
- Target answers never enter model input.
- Coding test runner rejects timeout/resource abuse and isolates execution.
- Synthetic forensic ground truth is independently checked.
- Unanswerable document tasks reward justified abstention.
- Evaluator changes create a new scoring version.

### Training tests

A tiny CPU/supported-device fixture verifies gradients update only intended parameters, loss masking, finite loss, checkpoint save/load and resume counters.

An optional real-device smoke verifies GPU identity, memory and one optimizer step. It is explicitly marked hardware-required and not run in ordinary CI.

Verify all-four-domain job counts, separate training seeds, adapter/base associations, no test-data training, artifact reload, conversion labeling and energy phase accounting.

### Report tests

A fixture with local-only results cannot generate cloud-energy claims. A fixture with invalid power cannot generate 0J efficiency. Empty/no-adequate cases remain visible. A reversed result direction changes the narrative rather than preserving an energy-premium claim.

### Acceptance checklist before main collection

- [ ] Meter and collector validation passed on the selected device.
- [ ] One request has complete output, terminal token counts and bracketing trace.
- [ ] Saved trace independently reproduces integrated energy.
- [ ] Runtime/device and model artifacts are pinned and verified.
- [ ] Dataset/splits/scoring are frozen and leakage checks passed.
- [ ] Schedule is seeded, counts verified and resume tested.
- [ ] Failed/partial attempts and unknown values survive export.
- [ ] Cloud use is explicitly enabled with dated prices and a hard cap, if used.
- [ ] Mentor reviewed the primary protocol and scope.
- [ ] Pilot findings justify main-trial durations/repetitions.

## 20 Run procedures and recovery

### Existing commands

These files exist today, but have the audit limitations above:

~~~bash
python src/test_connection.py
python src/run_benchmark.py
python src/analyze_results.py
python src/generate_graphs.py
python src/dashboard.py
python reports/generate_report.py
~~~

Some commands make hardware or paid API requests. Do not treat them as validation tests. Set cloud enabled false in the local config before a local-only inspection. Review current script arguments in source before using them.

The planned records/planner/training modules and config examples are not runnable commands yet. Implement CLI parsing, tests and documentation together. Do not advertise flags that do not exist.

### Before a session

1. Check hardware/firmware/software changes.
2. Confirm sufficient RAM/VRAM/disk and no unrelated intensive tasks.
3. Confirm model artifact, dataset hash and selected condition.
4. Check meter channel, clock behavior and a fresh sample.
5. Verify model placement, power profile, network and permitted data.
6. Create run directory, manifest and immutable schedule.
7. Estimate remaining time/spend and set stop limits.
8. Record unloaded/loaded baseline as applicable.
9. Run a small validation block before the full schedule.

### During a session

Watch collector heartbeat, largest sample gap, backend status, temperatures, memory, response completion and spend ledger. A dashboard is optional and its overhead must be controlled.

If collection fails, stop launching new measured trials. Finish/cancel the current request according to policy, preserve artifacts and mark measurement invalid. A functional response may still be useful for debugging but cannot repair missing energy.

If GPU OOM occurs, save the condition and error, confirm backend cleanup, then select a newly named lower-context/precision/batch condition. Do not change settings under the original condition ID.

### After a session

Flush/close all files, compute hashes, write final counts/status and back up private raw data. Validate references and reproduce a sample of energy calculations. Generate an exclusions report and inspect at least one trace from each major condition.

Do not delete failed runs after extracting successful outputs. Use a retention policy and record any removed raw artifacts with a reason.

### Recovery and resume

Resume links to the parent run and configuration hash. Revalidate hardware/runtime before continuing. If the environment changed, start a new run and analyze it as a new session/condition.

A process killed mid-training needs a recoverable checkpoint with optimizer/scheduler/RNG/global-step state where supported. Record lost work and energy rather than pretending training began at the resumed checkpoint without prior cost.

### Data publication

Export only reviewed public/synthetic content and approved summaries. Remove secrets, device/network identifiers and local paths from public manifests. Do not add application PDFs, transcripts or signed letters. Large model/data artifacts belong in appropriate storage with checksums and access/license information, not ordinary Git history.

## 21 Milestones and handoff

Use the calendar in research_plan.md. Prioritize reliable initial results for the April 2027 Expo, expanded work during 2027, and required completion by the approved end date. A spring 2028 Expo presentation does not extend SURF spending.

Suggested implementation work packages:

| Package | Deliverable | Done when |
| --- | --- | --- |
| WP01 | Records/config/store | Schemas and fixtures validate, resume preserves attempts |
| WP02 | Meter/energy | Numeric and device tests pass, uncertainty recorded |
| WP03 | Local backend | Actual counts, configured client, complete states, real trace |
| WP04 | Core planner | 240-trial matrix and pilot reviewed |
| WP05 | Domain suite/evaluation | 40 frozen tasks, source-aware splits and rubrics |
| WP06 | Cloud | Dated usage/cost, budgets, null/sourced energy |
| WP07 | Expanded inference | 480-trial target and selected larger-model studies |
| WP08 | LoRA pilot | Clean reload and held-out comparison in one domain |
| WP09 | Four-domain adaptation | Four pilots and feasible selected repeated jobs |
| WP10 | Scratch pilot | Small-model learning proof, bounded job, held-out report |
| WP11 | Analysis/report | Explicit runs, quality/failures, no unsupported conclusions |
| WP12 | Expo/final handoff | Reproducible figures, poster/report and limitations |

For each package, save implementation changes, tests run, fixture/hardware evidence, unresolved issues and the exact commit. Future implementation should create reviewable increments around these packages.

### Session notebook template

~~~text
Date/session ID:
Question and condition:
Code/config/dataset/model hashes:
Hardware/backend verified:
Baseline IDs and stability:
Planned/attempted/valid/adequate counts:
Meter gaps and uncertainty:
Training/device time and API spend:
Observed results:
Failures/exclusions:
Interpretation and alternative explanations:
Next action:
~~~

### Decisions still needed

- Final mentor-approved expanded scope and report title.
- Exact model artifacts/quantizations and a training base.
- Accepted meter update/gap/uncertainty policies after pilot.
- Corpus sources/licenses and domain evaluation rubrics.
- Supported ROCm/PyTorch/quantization combinations.
- Training search budget and seed counts after device-time pilot.
- Approved purchases, ownership, match and available spend timing.
- Actual presentation costs, if requesting travel.

No unresolved item is silently treated as approved.

## 22 Sources and unresolved decisions

Technical references checked October 16, 2026. Recheck compatibility/API behavior when executing; save the selected versions and source snapshots.

- Ollama completion metadata: https://docs.ollama.com/api/generate
- Ollama hardware support: https://docs.ollama.com/gpu
- ROCm Radeon Linux matrices: https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/native_linux/native_linux_compatibility.html
- Shelly Switch API: https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch/
- Shelly Plug US Gen4: https://kb.shelly.cloud/knowledge-base/shelly-plug-us-gen4
- PEFT concepts: https://huggingface.co/docs/transformers/peft
- From-scratch language-model example: https://huggingface.co/learn/llm-course/chapter7/6
- AMD fine-tuning example: https://developer.amd.com/playbooks/pytorch-finetuning/
- PyTorch deterministic operations: https://docs.pytorch.org/docs/stable/generated/torch.use_deterministic_algorithms.html
- Inference energy research: https://arxiv.org/abs/2311.16863

This guide's experiment sizes, pilot hyperparameters, schemas and acceptance procedures are proposed study design choices. They are not vendor guarantees, observed benchmark results or an approved grant commitment.
