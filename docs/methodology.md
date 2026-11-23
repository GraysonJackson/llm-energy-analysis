# Research methodology

This protocol supersedes the July scaffold methodology. It defines target research behavior; the current scripts still need the fixes in the [implementation guide](implementation_guide.md).

## Boundaries

Measure AC electricity supplied to the workstation at the wall, including CPU, GPU, RAM, storage, fans and PSU losses. Exclude displays and unrelated devices. State how the meter itself is powered and what its reading includes.

Keep unrelated workloads controlled and record background services. Hardware telemetry is diagnostic and does not replace wall measurement. Downloads and setup may be outside a request window but are recorded as separate overhead.

Meter this workstation during cloud tasks too, using the same outlet and task boundaries. Cloud client electricity includes the local harness, tool execution and local tests. Cloud API responses provide usage and latency. Provider server electricity is a separate evidence field. State whether external network energy is included when reporting a system total.

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

Measure the current workstation at the wall with no model loaded and no download in progress before the first AI measurement. Capture this before the model pulls if possible. Record at least 60 seconds and extend an unstable baseline. Save the trace and note the runtime's state and background work. For warm trials, separately measure the idle draw with that model loaded under the same conditions. Keep no-model idle, loaded-model idle, post-training idle, cold load and warm inference distinct in the run records.

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

For agentic coding, the local task measurement spans the entire job, including tools and tests. For each category, report pass rate and electricity per adequate result as total measured task electricity across attempts, including failures, divided by the count of adequate results. Show measurement coverage and leave the ratio unavailable if there are no adequate outcomes or energy coverage is incomplete.

Use public/synthetic data, source-aware splits and checks against exact/near-duplicate leakage. A held-out document's paraphrases must not appear in training data. Review a scoring subset with the mentor when possible.

## Training

Measure setup, optimization, validation, checkpointing, conversion and subsequent inference separately. Record successful-job and full-campaign energy, including failed jobs and hyperparameter searches. Do not double-count nested phase totals.

Compare adapters with the exact unchanged base on held-out tasks and a general-domain regression set. Record independent training seeds separately from inference repeats.

From-scratch work is a bounded small-model extension. Different architectures/tokenizers/pretraining histories prevent claims of equal-capability training comparisons.

## Cloud scenarios

A usable source specifies date, URL, workload/model context, units, input/output treatment, boundary and uncertainty. Unknown energy stays unavailable. Annual company energy or an unsourced constant is not a per-request observation.

### Source review as of November 22, 2026

The selected first-party endpoints are OpenAI Responses for `gpt-6.2-sol` and Anthropic Messages for `claude-sonnet-5-5`. Their model and API documentation support identifying requests and billed usage. This review found no published same-endpoint, same-workload provider measurement suitable for the primary comparison. Recheck the two providers and independent research before the evaluation is frozen and again before publication. [GPT-6.2 Sol documentation](https://developers.openai.com/api/docs/models/gpt-6.2-sol) · [Claude Sonnet 5.5 documentation](https://platform.claude.com/docs/en/models/sonnet-5-5/overview)

| Source and original value | What it supports | Limit for this study |
| --- | --- | --- |
| **0.67 Wh GPT-6.2 Sol and 0.54 Wh Claude Sonnet 5.5** for a modeled 400-input, 300-output token message, dated November 18, 2026. [Pentos method and estimates](https://www.pentos.ai/wiki/chats/energy-usage/) | A common short-message sensitivity example using both selected model names. | Third-party estimates with assumed architecture and serving factors. The source uses a comparable model or size class for GPT and EcoLogits assumptions for Claude. No measured server trace or matching workload for our tasks. |
| **0.31 Wh median, 0.16–0.60 Wh interquartile range**, April 2026. [Oviedo et al., *Joule*](https://www.microsoft.com/en-us/research/publication/energy-use-of-ai-inference-efficiency-pathways-and-test-time-scaling/) | Peer-reviewed bottom-up model of optimized, large-scale inference. Useful external context for short requests. The authors find substantially higher demand for some long reasoning and agentic workloads. | Cross-scenario distribution under modeled conditions. The interquartile range is specific to the paper and does not give uncertainty bounds for either endpoint. |
| **8.6–26 Wh Claude Sonnet 5.5 at high effort** for an external CursorBench coding workload, November 2026. [Projet Celsius analysis](https://projetcelsius.com/en/blog/fable-5-2-opus-5-5-energy-water/) | An example of how a multi-call coding workload can differ from a short message. | Estimated from external token usage and assumed model size inferred from price. Keep as context only. The task, agent setup and energy factors differ from ours. |
| **0.34 Wh average ChatGPT query**, June 2025. [OpenAI CEO's public statement](https://blog.samaltman.com/the-gentle-singularity/) | Historical provider statement about the consumer service. | The statement gives no measurement method or selected API model attribution. Keep as historical context only. |
| **0.24 Wh median Gemini Apps text prompt**, for May 2025 workloads. [Google technical report](https://services.google.com/fh/files/misc/measuring_the_environmental_impact_of_delivering_ai_at_google_scale.pdf) | Example of published production measurement and its system boundary. | Different provider, product and workload. Use to illustrate the evidence standard. |

Prioritize measurements tied to the exact deployed model, endpoint, task or token mix, serving tier, and accounting boundary. If a provider or independent researcher instead supplies a transparent estimate, retain its factors and uncertainty and label the result as modeled. Prefer sources that distinguish input, cached input, output and reasoning and disclose how batching, hardware and PUE are handled. Keep rejected proxies in this register with the reason for exclusion. A [recent third-party model](https://arxiv.org/abs/2609.33965) separates input and output, but bins proprietary deployments into assumed size classes. Use such models for sensitivity analysis only when their assumptions can be documented and compared with our workload.

~~~text
J_per_token_from_kWh_per_1000_tokens =
  source_value * 3_600_000 / 1000
~~~

Apply PUE only to IT-only energy that excludes facilities. Avoid multiplying whole-facility estimates again. Show low/central/high assumptions where justified and label them as scenarios.

If the main result lacks credible server-side evidence, report the server value as unavailable and show a break-even threshold on paired completed tasks at comparable quality. For the same task and energy basis, `cloud_server_break_even_Wh = local_workstation_Wh - cloud_client_workstation_Wh` when other energy components are excluded. If a credible external-network estimate is included, subtract it as well. A negative result means the measured cloud client alone used more electricity for that pair. Report coverage, meter uncertainty and gross versus baseline-subtracted thresholds separately. Never apply a short-message figure to every step of an agent task. Report the measured local client and any estimated facility components separately before showing their scenario sum.

Each provider has a $10 USD cap across the research campaign, including pilots, probes, paid retries and evaluators. Standard text prices checked November 22, 2026 are $2 per million input tokens and $10 per million output tokens for both selected endpoints. Use standard interactive processing, account for cached and reasoning usage according to each provider, and recheck prices at collection. Before requesting a paid call, reserve its conservative maximum cost in a persistent ledger. Reconcile billed usage afterward and retain a reservation when billing is uncertain. Cover every task once on both services first. Schedule any repeats on the same preregistered, category-balanced subset, stopping before either provider would exceed its cap. [OpenAI pricing](https://developers.openai.com/api/docs/models/gpt-6.2-sol) · [Anthropic pricing](https://platform.claude.com/docs/en/models/sonnet-5-5/overview)

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
