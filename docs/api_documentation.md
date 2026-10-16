# Existing API reference and implementation limits

Audited October 16, 2026 against e712d8d8ce7041b87d26f81542ec53fc0b41bc2c. This describes the current scaffold, not the planned architecture. Use the [implementation guide](implementation_guide.md) for target contracts and fixes.

## PowerMonitor

Module: src/power_monitor.py.

Constructor: PowerMonitor(ip_address, polling_interval=1.0, timeout=5).

| Method | Current behavior |
| --- | --- |
| test_connection() | Calls legacy /status and returns a boolean |
| get_current_power() | Parses legacy meters[0].power or top-level apower; returns float or None |
| start_monitoring() | Resets state and sets flags; does not start a background collector |
| record_measurement() | Explicitly obtains and appends one measurement |
| stop_monitoring() | Stops session and integrates samples already in memory |
| get_measurements() | Returns a shallow copy of sample list |
| measure_baseline(duration=60) | Loops over record_measurement then returns session statistics |
| monitor_during_task(task_func, *args, **kwargs) | Runs a polling thread around a task; not used by current local benchmark path |
| export_to_csv(filepath) | Exports collected measurement rows |

When samples exist, stop_monitoring returns duration_sec, measurement_count, avg_power_w, min_power_w, max_power_w, energy_joules and energy_wh. With no samples it returns only duration_sec/measurement_count. A no-sample summary is not 0J evidence.

The thread helper is a starting point, not a validated lifecycle: boundary samples, exceptions, synchronization, finite shutdown, gaps and field provenance need the guide's changes. Generation-specific meter adapters are not implemented.

## LocalLLMBenchmark

Module: src/local_llm_benchmark.py.

Constructor takes host, temperature, top_p and timeout. The current constructor does not retain the client it creates; module-level Ollama calls do not reliably honor the configured client.

| Method | Current behavior/limit |
| --- | --- |
| test_connection(), list_models() | Module-level SDK calls; response-shape compatibility needs testing |
| count_tokens(text, model) | len(text)//4 approximation, unsuitable for research token metrics |
| generate(model, prompt, max_tokens=1000) | Streams output; approximate counts; timeout can still lead to success=True |
| benchmark_prompt(model, prompt_data, power_monitor=None) | Starts/stops meter session without polling continuously |
| run_warmup(model, count=3) | Very short ready queries; does not prove representative thermal stability |
| benchmark_model(...) | Fixed-order repetitions/cooling; no immutable planner/resume |
| export_to_csv(results, filepath) | Writes selected summary fields; omits response and error details |

Current local CSV fields:
timestamp, model, prompt_id, prompt_category, repetition, input_tokens, output_tokens, total_tokens, generation_time_sec, time_to_first_token_sec, tokens_per_sec, power_start_w, power_end_w, power_avg_w, energy_joules, joules_per_token, success.

Current joules_per_token uses input-plus-output tokens. The target design names output-token and total-token denominators separately.

## CloudBenchmark

Module: src/cloud_benchmark.py. Constructor accepts the legacy config and initializes enabled clients if corresponding environment keys exist.

Methods: test_connections, generate_openai, generate_anthropic, benchmark_prompt, benchmark_providers, export_to_csv. Private helpers currently use hardcoded historical combined-token prices and unsupported energy defaults.

Connection probes themselves generate requests using historical model IDs. They can cost money and fail independently of a configured current endpoint. Replace probes and count their usage.

Current cloud CSV fields:
timestamp, provider, model, prompt_id, prompt_category, repetition, input_tokens, output_tokens, total_tokens, response_time_sec, cost_usd, estimated_energy_joules, joules_per_token, success.

Provider usage and client latency can be observed; fixed electricity factors are not measurements. Current exports omit response/error text and source provenance.

## Orchestration

src/run_benchmark.py loads root config.yaml and data/prompts.json, creates output folders, connects components and runs baseline/local/cloud stages.

The current main runner does not implement the proposed YAML schema, run manifests, explicit trial plans, resumable scheduling or training. Legacy CONFIG_PATH in .env.example is not a supported override in its current main path.

A missing meter can lead to functional-only operation. Such results must not enter energy analysis as measured zero consumption.

## Analysis, graphs and reports

BenchmarkAnalyzer currently selects the newest local/cloud/baseline files independently and filters success=True. This can mix sessions and omit failure accounting.

GraphGenerator and GrantReportGenerator are existing scaffolds, not validated reporting tools. Replace fixed privacy scoring, ambiguous denominators, source-less cloud estimates and predetermined conclusions before using their output as research findings.

src/dashboard.py has independent state/polling and latest-file lookup. The target is a read-only observer of explicit run records. Do not use its separate collector as evidence that benchmark sampling works.

## Target interfaces

The proposed record schemas, adapters, planner, evaluation, training jobs and failure semantics are specified in implementation_guide.md and examples/. Those modules/interfaces are not implemented by this documentation change.
