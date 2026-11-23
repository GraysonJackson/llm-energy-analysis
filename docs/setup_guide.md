# Setup guide

The repository currently contains a benchmark scaffold. Follow the P0 fixes and acceptance tests in the [implementation guide](implementation_guide.md) before collecting research measurements. Setup success is not measurement validation.

## First check on the installed workstation

The Ryzen 5 5600G and RTX 5060 Ti 16 GB are recorded in the [hardware inventory](hardware_and_funding.md). On this workstation, the Shelly address is set as `SHELLY_IP` in the ignored `.env` file. Ollama is the local runtime for this project. Both cloud providers are disabled.

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

The full runner still needs continuous per-request sampling, runtime token counts, and matched baselines. Those changes and a one-prompt pilot come before research collection.

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

For research, record the exact model digest, tokenizer, template, quantization, context and reasoning settings. The original Llama 3 8B and Mistral 7B were planning candidates. Use the same public or synthetic prompts and rubric across local and cloud models. GPT-6.2 Sol and Claude Sonnet 5.5 are comparison candidates as of November 22, 2026. The legacy cloud runner needs an update before enabling them. [OpenAI model catalog](https://developers.openai.com/api/docs/models) · [Claude model catalog](https://platform.claude.com/docs/en/models/overview)

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
