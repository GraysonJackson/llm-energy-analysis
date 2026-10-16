# Research methodology

This protocol supersedes the July scaffold methodology. It defines target research behavior; the current scripts still need the fixes in the [implementation guide](implementation_guide.md).

## Boundaries

Measure AC electricity supplied to the workstation at the wall, including CPU, GPU, RAM, storage, fans and PSU losses. Exclude displays and unrelated devices. State how the meter itself is powered and what its reading includes.

Keep unrelated workloads controlled and record background services. Hardware telemetry is diagnostic and does not replace wall measurement. Downloads and setup may be outside a request window but are recorded as separate overhead.

Cloud API responses provide output, latency, token usage and billing data. They do not directly measure provider-server electricity. Electricity used by the local API client is a separate boundary.

## Integration

Use UTC for traceability and monotonic time for intervals. Record meter-request send/receive times and device timestamps if available. A host midpoint timestamp is an approximation with polling-latency uncertainty.

Collect before/during/after generation. Clip the trace to the defined request interval and interpolate only between valid bracketing samples within the accepted gap policy. Do not extrapolate missing boundaries.

~~~text
E_gross_J = sum((P_i + P_i_plus_1) / 2 * delta_t_seconds)
E_gross_Wh = E_gross_J / 3600
E_gross_kWh = E_gross_J / 3_600_000
E_incremental_J = E_gross_J - idle_mean_W * request_duration_s
~~~

Preserve negative incremental values and flag baseline/uncertainty review. Unknown or invalid energy is null with a reason, not zero. Time-weighted mean power is energy divided by duration.

Approximately one-second polling is a starting setting, not a guarantee of the meter's actual update rate or accuracy. Measure timing, stale updates, gaps and uncertainty in the pilot. Short requests may require repeated batches; per-request batch averages are amortized estimates.

## Baselines and state

Measure at least 60 seconds of relevant idle state and extend unstable baselines. Distinguish no-model idle, loaded-model idle, post-training idle, cold load and warm inference.

Warm-up electricity and runtime are recorded as setup overhead and excluded from steady-state averages. Fixed pauses alone do not establish thermal stability. Bracket blocks with baselines where feasible and retain drift/variance.

Keep cache state explicit. A model that unloaded during cooldown is not a warm trial.

## Tokens and latency

Use runtime-reported counts, including Ollama completion metadata. Stream chunks and len(text)//4 are not valid replacements for actual token counts.

Report input/output tokens, token source, completion reason, client latency, streamed first-nonempty-answer latency, runtime decode duration and loading time separately where available. Unavailable timing is null.

Joules per generated output token and joules per total input-plus-output token are distinct metrics. Cross-model tokenizers produce different units of work; quality and energy per adequate task response are primary comparison context.

## Controls

Freeze dataset/split hashes, model revision/digest, tokenizer, template, quantization, generation parameters, context/output caps, backend, offloading, power profile and software versions.

Use seeded prompt/block randomization and distribute repetitions across sessions. The original suite starts with three repeats; pilot variance determines whether more are needed. Repeats of one prompt are not independent task samples.

GPU-only claims require verified placement. If CPU, PSU, OS and GPU change together, report a system comparison. Match unchanged components where practical.

## Quality

Execution completion is separate from adequate output. Preserve wrong answers, empty outputs, truncation, invented evidence and failed code tests. Define adequacy before collection and retain domain-specific rubrics.

Use public/synthetic data, source-aware splits and checks against exact/near-duplicate leakage. A held-out document's paraphrases must not appear in training data. Review a scoring subset with the mentor when possible.

## Training

Measure setup, optimization, validation, checkpointing, conversion and subsequent inference separately. Record successful-job and full-campaign energy, including failed jobs and hyperparameter searches. Do not double-count nested phase totals.

Compare adapters with the exact unchanged base on held-out tasks and a general-domain regression set. Record independent training seeds separately from inference repeats.

From-scratch work is a bounded small-model extension. Different architectures/tokenizers/pretraining histories prevent claims of equal-capability training comparisons.

## Cloud scenarios

A usable source specifies date, URL, workload/model context, units, input/output treatment, boundary and uncertainty. Unknown energy stays unavailable. Annual company energy or an unsourced constant is not a per-request observation.

~~~text
J_per_token_from_kWh_per_1000_tokens =
  source_value * 3_600_000 / 1000
~~~

Apply PUE only to IT-only energy that excludes facilities. Avoid multiplying whole-facility estimates again. Show low/central/high assumptions where justified and label them as scenarios.

Use separate dated input/output/cache prices and provider-specific billing semantics for API cost. Count probes, retries and evaluator usage toward the budget.

## Analysis and claims

Select explicit runs and verify compatibility rather than choosing latest files independently. Retain counts for attempts, completed, valid, adequate and excluded outputs, with reasons.

Report paired task differences, means/medians, variation, quality and failure rates. Cluster uncertainty estimates by independent prompts/source groups as appropriate. Record method/sample sizes and avoid broad claims from small pilots.

Measure operational electricity. Lifecycle carbon, water use, universal environmental superiority and a causal energy price for privacy are outside what these observations alone establish.

## References

- [Ollama generation](https://docs.ollama.com/api/generate)
- [Shelly Switch API](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch/)
- [Shelly Plug US Gen4](https://kb.shelly.cloud/knowledge-base/shelly-plug-us-gen4)
- [Inference energy research](https://arxiv.org/abs/2311.16863)

Checked October 16, 2026. Verify actual device/firmware performance; no unsupported absolute meter-accuracy claim is assumed.
