# Setup guide

The repository currently contains a benchmark scaffold. Follow the P0 fixes and acceptance tests in the [implementation guide](implementation_guide.md) before collecting research measurements. Setup success is not measurement validation.

## First check on the installed workstation

The Ryzen 5 5600G and RTX 5060 Ti 16 GB are recorded in the [hardware inventory](hardware_and_funding.md). On this workstation, the Shelly address is set as `SHELLY_IP` in the ignored `.env` file. Ollama is the local runtime for this project. Paid receipt requests use the explicit command below.

When ready, run from the repo root in PowerShell:

```powershell
.\.venv\Scripts\python.exe src/test_connection.py --shelly-only
.\.venv\Scripts\python.exe src/capture_idle_baseline.py --seconds 120
ollama pull gemma4:12b-it-q4_K_M
ollama pull gpt-oss:20b
ollama pull qwen3.8:27b
.\.venv\Scripts\python.exe src/test_connection.py
```

The first command reads Shelly wattage. Before the second command, make sure no model is loaded, no download is in progress, and unrelated workloads are quiet. The idle capture writes a raw trace to the ignored `runs/baselines/` directory. Record the Shelly model, firmware and workstation state in the run notes. Review trace coverage and stability before using the baseline. The pull commands download the three models. The last command checks wattage and confirms that Ollama lists all three. If HTTP access is restricted, confirm the plug's authentication and permitted network path before continuing.

Once all three models answer a short smoke prompt at the shared 8,192-token context, run the local direct pilot separately. The full agent and cloud comparison still requires its own harness and validation.

## First measured direct pilot

Unload any active models and keep unrelated workstation activity quiet. From the repo root, run the email task eight times per model under the same settings. The extra repeats leave more time for meter samples when brief responses finish quickly.

```powershell
.\.venv\Scripts\python.exe src/run_direct_pilot.py --task P-D02 --repetitions 8
```

The runner loads one model at a time, verifies the reported context, waits 60 seconds for settling, and captures 120 seconds of loaded idle before sending the same task at 8,192 context tokens. Attempts, model placement, native token counts, and raw traces are saved in `runs/direct_pilot_*/`. The short direct-task calibration requests `think: false` for all models. Ollama uses the lowest supported level when a model cannot disable thinking. The API timeout is 90 seconds and the shared generation cap is 1,024 tokens. The manifest records these settings, and each attempt retains available cache counts and the completion reason. [Ollama thinking controls](https://docs.ollama.com/capabilities/thinking)

Energy covers the whole batch of sequential requests. Gross energy is unavailable if there are fewer than two usable samples inside the workload window, either boundary lacks coverage, a contributing reading fails, or an integration gap exceeds 2.5 polling intervals. The runner also withholds idle-adjusted energy if the spread between the three loaded-idle segment means exceeds 3 W or 5% of the full idle mean, whichever is larger. This is a provisional screening rule for the pilot, independent of meter accuracy. Check `Completed attempts`, `Pilot status`, and the saved responses before grading or comparing energy. Repeated prompts can reuse cached inputs. Treat these as a warm batch condition and report recorded cache counts. Use `--all-direct` only after reviewing the first traces and adequate responses.

## Structured extraction across different receipts

Run the eight synthetic receipts in the extraction follow-up, three times each per model:

```powershell
.\.venv\Scripts\python.exe src/run_direct_pilot.py --receipt-variants --repetitions 3
```

This is a separate dataset from the original pilot. All three models receive the same receipts in the same order, using the same generation settings and loaded-idle procedure. The runner saves the dataset and scoring hashes in the manifest, then writes `receipt_scores.json` after the measured workload ends. The score requires raw JSON with the exact keys, values, and types. It rejects Markdown wrappers, duplicate keys, and inferred values for missing fields. The energy per valid response includes the wall energy of failed attempts and is unavailable if there are no passes or no valid workload trace. Energy is measured for the full receipt batch per model. Scores are also listed by receipt.

## Paid cloud receipt pilot

Add `OPENAI_API_KEY` and `GEMINI_API_KEY` to the ignored `.env` file or your environment. Use the OpenAI project enrolled in the data-sharing offer and a Gemini API project with active billing and access to Gemini 4 Neon. Keep Ollama running with no loaded models, keep other workloads quiet, and run one pilot at a time. When ready to send the synthetic prompts from the repo root, run the following command.

```powershell
.\.venv\Scripts\python.exe src/run_cloud_receipt_pilot.py --execute
```

GPT-5.4 (`gpt-5.4-2026-03-05`) and Gemini 4 Neon (`gemini-4-neon`) each receive the same eight synthetic prompts once, in dataset order. The pilot uses fresh requests, each provider's low reasoning setting, a 1,024-token output cap that includes thinking, and the same strict scorer as Ollama. Schema enforcement and tools are absent. The APIs use their native context windows for these short prompts. The OpenAI request sets `store: false` for later response retrieval. Account-level data sharing still applies. [OpenAI model settings](https://developers.openai.com/api/docs/models/gpt-5.4) · [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data) · [Gemini model settings](https://aistudio.google.com/docs/whats-new-gemini-4-neon)

This runner applies cumulative limits of $5 USD for OpenAI and $10 USD for Gemini in this checkout, before discounts or credits. Before each request, `runs/cloud_budget.sqlite3` reserves for up to 7,168 input tokens and 1,024 output tokens at conservative standard rates. The pilot accepts at most 1,024 UTF-8 bytes of prompt text per request. Reported usage replaces the reservation. Unconfirmed requests keep their reservations, and the pilot stops without retrying them. Keep the ledger across runs. Check OpenAI's Usage page for the data-sharing incentive and both dashboards for actual costs. The OpenAI quota is shared across eligible traffic, and requests that exceed the remaining daily quota are billed at list price. Prices were checked November 25, 2026. [OpenAI incentive](https://help.openai.com/en/articles/10306912-sharing-feedback-evaluation-and-fine-tuning-data-and-api-inputs-and-outputs-with-openai) · [OpenAI pricing](https://developers.openai.com/api/docs/models/gpt-5.4) · [Gemini pricing](https://aistudio.google.com/docs/pricing#gemini-4-neon)

After a three-minute settle, each provider gets its own two-minute workstation idle baseline and a separate Shelly trace for its eight requests. `runs/cloud_receipt_pilot_*/` holds the per-provider traces, attempt logs, a manifest, and `receipt_scores.json` after a full paired run. The energy values cover the client workstation at the wall, including the time it waits for API replies. Cloud server energy requires separate evidence. The scorer withholds energy if power coverage is too sparse and withholds idle-adjusted energy if the idle trace drifts. Compare strict pass rates by matching receipt ID and report the different numbers of repeats. Treat this run as a receipt-only pilot.

## Seven-task direct comparison

Use the cloud keys and workstation setup above. From the repo root, pair the seven direct tasks with the saved 63 local attempts using the following command.

```powershell
.\.venv\Scripts\python.exe src/run_cloud_receipt_pilot.py --all-direct --local-run runs/direct_pilot_20261124T184753_704291Z --execute
```

The runner checks the local task hash and attempts before sending the exact same seven prompts to each cloud model once. It reuses the cloud ledger and captures an idle baseline and workload trace per provider. The results folder contains `direct_comparison.json` with attempt status, latency, and full-block energy. The same file includes each model's first attempt on each task and its counts across all repetitions. Compare quality by task category. The local blocks cover three repetitions and the cloud blocks cover one, so compare full-block energy with the attempt counts and energy scopes in view.

The comparison scores raw JSON extraction automatically and marks incomplete responses inadequate. For the other answers, use `review_packet.md` and record the verdicts in `review_grades.json`. The packet shuffles answer order within each task and hides model names and timings. Keep `review_key.json` out of view while grading. The standalone Python function is reviewed manually against the rubric and reference cases. Refresh the comparison after grading using the results folder printed by the runner. This command works offline.

```powershell
.\.venv\Scripts\python.exe src/review_direct_pilot.py runs/cloud_direct_pilot_<run-id>
```

## Five-task agentic Python pilot

Start Docker Desktop with its local Linux engine. From the repo root in PowerShell, load the Python worker image and check isolation before starting the measured run. The image download and check are outside all measurement windows.

```powershell
docker pull python:3.12-slim
.\.venv\Scripts\python.exe src/run_agent_pilot.py --check
```

Leave Docker and Ollama running, with no Ollama models loaded. Keep the Shelly reachable and other workloads quiet. The same API keys and spend ledger used for the direct pilot apply here. Run this command when ready to start measurement and send paid requests.

```powershell
.\.venv\Scripts\python.exe src/run_agent_pilot.py --execute
```

All five models get one attempt at each of the five agent tasks. Each attempt starts from the same task files and uses the same tool protocol for listing, reading, writing, running public checks, and submitting a summary. The same seeded task order applies to each model. A task allows 14 turns and up to 10 minutes. A turn has an 8,192-token working context and a 2,048-token generation cap, including reasoning where the provider bills it as output. The prompt carries a bounded recent tool history. For cloud attempts, synthetic workspace excerpts and public tool results become part of the prompt and the OpenAI project’s data-sharing terms apply. [Pilot tasks and paired rules](datasets_and_evaluation.md#paired-pilot-v1)

The worker runs generated Python with an unprivileged user, isolated networking, a read-only container root and temporary storage. It receives no host workspace mounts or API credentials. The manifest records the exact image ID. The measured batches include public tests and model waits. Hidden checks run separately on disposable copies after the measured batches finish. Refactor answers that pass the automated checks go into `refactor_review.md`. Record the shared-loop and order-explanation verdicts in `refactor_review.json`. [Docker runtime options](https://docs.docker.com/reference/cli/docker/container/run/) · [Docker none network](https://docs.docker.com/engine/network/drivers/none/)

`runs/agent_pilot_*/` holds the manifest, attempt snapshots and tool logs, raw Shelly traces, and `agent_scores.json`. Each model gets its own idle baseline. Local models are loaded during idle, and cloud blocks have no local model loaded. Cloud traces cover the workstation, including the agent’s local public tests. With unstable idle, the runner withholds idle-adjusted energy. Use `--grade-run` with the saved folder to run grading again without model requests or metering.

## Unattended benchmark

Use the same `.env`, Shelly, Docker worker image and local Ollama models as the pilots. Keep the PC awake and other workloads quiet. Start with no Ollama models loaded and keep the PowerShell window open. The plan command validates the task packets without starting Docker, Ollama, the meter or paid calls.

```powershell
.\.venv\Scripts\python.exe src/run_benchmark_day.py --plan
```

Start the unattended run when ready to send paid requests.

```powershell
.\.venv\Scripts\python.exe src/run_benchmark_day.py --execute
```

This campaign schedules one pass per model across 49 direct tasks in seven categories, eight receipt variants, and five agentic Python tasks. One additional calibration task per model checks the structured read, edit, and test interface before its agentic section. Calibration is outside the measured batches. Each measured block uses the Shelly in sequence. The new agent interface requests the same one-action schema across providers. It also requests Ollama's named `low` setting for GPT-OSS and logs completion metadata. Direct and receipt prompts continue to use plain-text responses, with strict JSON grading where required. The original prompt-only agent run remains a separate condition. [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs) · [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) · [Gemini structured outputs](https://aistudio.google.com/docs/structured-output)

Open `benchmark_report.md` in the printed `runs/benchmark_day_*/` folder. It records each section's status, power coverage, task scores, pending reviews, and the budget ledger. Each section folder holds its raw attempts and traces. The existing $5 OpenAI and $10 Gemini cumulative limits apply before credits. If a model fails calibration its agentic tasks are marked skipped. Model or provider failures are kept in the report, and unrelated blocks can continue. Use `--execute --resume` with the campaign folder to run pending blocks. Previously completed or partial blocks remain on disk and are not replayed.

The direct and refactor review packets hide the model labels. When you finish editing their grade files, refresh the report without model calls or meter activity. Substitute the printed folder name.

```powershell
.\.venv\Scripts\python.exe src/run_benchmark_day.py --refresh runs/benchmark_day_<run-id>
```

The report covers task quality, latency, and workstation electricity. Provider retention controls, actual billing and credits, cloud-server energy evidence, and the proposed training experiments remain separate study work.

### Targeted follow-ups

If a benchmark hit an ambiguous Gemini timeout, use the saved campaign to plan a follow-up. `--plan` lists the remaining requests without starting a run. Change `--plan` to `--execute` when ready. The follow-up gets its own report and power traces. It includes undispatched direct prompts and the skipped receipt block. The original attempt log retains the timed-out request and its reservation.

```powershell
.\.venv\Scripts\python.exe src/run_benchmark_day.py --plan --recover-gemini runs/benchmark_day_20261126T164014_770018Z
```

Use `--execute --agent-only` to recalibrate all five models and rerun only passing models' agent tasks. The v3 interface reads only the fields used by the chosen action. GPT-OSS uses Ollama’s native tool envelope for the same permitted operations. Treat v3 as a separate agent-interface condition from the original campaign. [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling)

### Offline inference and repeat measurements

For the privacy check with Ethernet connected, open PowerShell as Administrator and leave Ollama running with no models loaded. From the repo root, run:

```powershell
.\.venv\Scripts\python.exe src/check_offline_inference.py --firewall
```

The check temporarily blocks non-loopback IPv4 and IPv6 outbound traffic for the standard Ollama installation’s executables. It verifies the active rules and the loopback listener before, between, and after inference. If the check reports an existing non-loopback Ollama connection, restart Ollama and try again. The rules are removed at exit. If PowerShell was force-closed, use the exact group printed at startup or saved in `offline_inference.json` in the following Administrator PowerShell cleanup command. [Windows Firewall rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)

```powershell
Get-NetFirewallRule -PolicyStore PersistentStore -Group '<printed-firewall-group>' | Remove-NetFirewallRule
```

For whole-workstation isolation, disconnect the workstation's Wi-Fi, Ethernet and VPN in Windows, run the command below, then reconnect once it prints the evidence path. This mode records physical-adapter and default-route counts before and after the requests. Both modes contact Ollama through loopback and record neither power nor packets.

```powershell
.\.venv\Scripts\python.exe src/check_offline_inference.py
```

The repeat panel fixes two direct tasks per category and includes the eight receipts. Its selection uses only the frozen task IDs, category labels and seed. Each invocation measures one more pass per model in a new folder. Use `--plan` to print the exact selected IDs before `--execute`. Keep sessions separate when estimating repeatability. Use the original full campaign to describe coverage of the 62-task suite.

```powershell
.\.venv\Scripts\python.exe src/run_benchmark_day.py --plan --repeat-panel
```

## 1 Inspect existing code

Clone/open the repository and work from its root:

~~~bash
python -m venv .venv
~~~

Linux activation:

~~~bash
source .venv/bin/activate
~~~

PowerShell activation:

~~~powershell
.venv\Scripts\Activate.ps1
~~~

Then:

~~~bash
python -m pip install -r requirements.txt
python -m compileall -q src reports
~~~

The dependency file has broad minimum versions. Record a tested inference environment lock. Create a separate training environment; the current requirements do not provide a complete ROCm/PyTorch/PEFT stack.

## 2 Inventory hardware

Record CPU/GPU/motherboard, BIOS, RAM layout/speed, SSD capacity/free space, PSU, cooling, OS/kernel and power profile.

The installed pilot uses the Ryzen 5 5600G and RTX 5060 Ti 16 GB. The earlier RTX 3070 configuration is the historical baseline. See the [hardware inventory](hardware_and_funding.md) for verified and previously recorded details.

Capture a baseline before changing multiple components if practical. Otherwise report a whole-system comparison.

## 3 Choose a supported GPU stack

The current pilot uses the NVIDIA GPU. For future AMD inference, use the Ollama hardware list and ROCm Radeon matrix for the exact OS and card.

Verify actual discrete-GPU execution and detect CPU/iGPU fallback. Save runtime/driver/device versions and a small workload trace. Do not copy an arbitrary CUDA install command into the AMD environment.

For training, independently validate one forward/backward/optimizer step, memory use, save/reload and the quantization backend before a long job.

Sources:
- https://docs.ollama.com/gpu
- https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/native_linux/native_linux_compatibility.html

## 4 Select exact models

Start with **Gemma 4 12B Q4_K_M** (`gemma4:12b-it-q4_K_M`). Ollama lists the artifact at 8.0 GB, which leaves more VRAM for context and runtime overhead. Start at 4K context, run one model at a time, and use `ollama ps` after a manual prompt to record processor placement and context. An artifact's download size alone cannot establish GPU fit. [Gemma 4 artifact](https://ollama.com/library/gemma4:12b-it-q4_K_M) · [Ollama context and placement](https://docs.ollama.com/context-length)

The other two local candidates are `gpt-oss:20b` and `qwen3.8:27b`. Ollama lists the GPT-OSS MXFP4 artifact at 14 GB, so verify placement at the same context length. The standard Qwen artifact is 18 GB. Record the CPU/GPU split as part of that configuration. [GPT-OSS artifact](https://ollama.com/library/gpt-oss:20b) · [Qwen 3.8 tags](https://ollama.com/library/qwen3.8/tags)

Use Ollama for scripts because the repo already targets its API and the response includes native token counts and timing. LM Studio is also an option for interactive trials and GPU offload tuning. Record it as another runtime if you measure it. [Ollama generation API](https://docs.ollama.com/api/generate) · [LM Studio API](https://lmstudio.ai/docs/developer/core/server)

For research, record the exact model digest, tokenizer, template, quantization, context and reasoning settings. The original Llama 3 8B and Mistral 7B were planning candidates. Use the same public or synthetic prompts and rubric across local and cloud models. The paid receipt pilot selects GPT-5.4 and Gemini 4 Neon directly. Use that pilot command for the cloud receipt comparison. [OpenAI model catalog](https://developers.openai.com/api/docs/models) · [Gemini model catalog](https://aistudio.google.com/docs/models)

Inspect local inventory:

~~~bash
ollama --version
ollama list
~~~

Select additional variants after measuring memory use at the intended context length.

## 5 Meter and network

Record the device model and firmware. The connection check tries the read-only `Switch.GetStatus` RPC with `apower` first, then the legacy `/status` endpoint. Confirm the reading is plausible for the connected workstation. [Shelly Switch status](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch/)

Use a placeholder such as METER_HOST in local instructions; keep real network details private. Confirm a permitted network path between collector and meter. If that cannot work, choose a locally logging measurement arrangement.

Verify polling/update interval, latency, coverage, stable loads, cumulative energy where supported and uncertainty. Keep only the workstation behind the measured outlet. Do not use relay-control calls during experiments.

## 6 Local configuration and credentials

`config.yaml` selects Gemma 4 12B, GPT-OSS 20B, and Qwen 3.8 27B for local setup. It retains historical cloud examples with both providers disabled. The planning example under `docs/examples` describes a future configuration schema.

On a fresh checkout, copy the template to create a local `.env` and fill in `SHELLY_IP`. Use the file already present on this workstation:

~~~bash
cp .env.example .env
~~~

PowerShell equivalent:

~~~powershell
Copy-Item .env.example .env
~~~

Keep real keys in the local environment. The legacy .env.example CONFIG_PATH setting is not an implemented config override in the current main runner. Read the implementation before assuming environment variables or flags are honored.

Validate active cloud endpoint availability and current separate input/output pricing before enabling paid calls. Remove unsupported energy factors from research interpretation rather than using them as facts.

## 7 Validate before collecting

Implement and pass synthetic energy, adapter, token-count, completion-state, run-store and budget tests. Run one complete request with actual output/tokens and a bracketing power trace, then independently recompute energy.

A missing meter permits functional debugging only. Do not interpret existing exported zero-energy values as findings.

## 8 Legacy commands

Existing entry points:

~~~bash
python src/test_connection.py
python src/run_benchmark.py
python src/analyze_results.py
python src/generate_graphs.py
python src/dashboard.py
python reports/generate_report.py
~~~

These can perform hardware/API calls and are not unit tests. Some paths still contain the known bugs documented in the guide. Keep dashboard bound to localhost and stop it for controlled runs unless its overhead is intentionally included.

Future planner/training commands must be documented only after implementation. No training CLI exists in the audited code.
