# Setup guide

The repository currently contains a benchmark scaffold. Follow the P0 fixes and acceptance tests in the [implementation guide](implementation_guide.md) before collecting research measurements. Setup success is not measurement validation.

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

Existing baseline is Ryzen 5 5600G/RTX 3070/32GB/WD_BLACK SN770 1TB on B550 Phantom Gaming 4/ac with BIOS P2.10. The proposed R9700 and 5900XT are not installed/validated. Check exact board firmware prerequisites and component compatibility before replacing parts.

Capture a baseline before changing multiple components if practical. Otherwise report a whole-system comparison.

## 3 Choose a supported GPU stack

For AMD inference, use the current Ollama hardware list and ROCm Radeon matrix for the exact OS/card. R9700 Linux support is listed in Ollama's current documentation; that does not establish identical Windows or training support.

Verify actual discrete-GPU execution and detect CPU/iGPU fallback. Save runtime/driver/device versions and a small workload trace. Do not copy an arbitrary CUDA install command into the AMD environment.

For training, independently validate one forward/backward/optimizer step, memory use, save/reload and the quantization backend before a long job.

Sources:
- https://docs.ollama.com/gpu
- https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/native_linux/native_linux_compatibility.html

## 4 Select exact models

Use current available artifacts and licenses; record exact digest/revision, tokenizer, template and quantization. Original core candidates are Llama 3 8B and Mistral 7B.

Inspect local inventory:

~~~bash
ollama --version
ollama list
~~~

Select exact variants after memory checks. Do not blindly pull a 70B model from the legacy config. The 32GB card's capacity does not guarantee arbitrary model/context/training fit.

## 5 Meter and network

Identify actual device model/firmware. Verify a read-only endpoint and payload for that generation; Gen1 /status assumptions do not validate Gen4. For a compatible modern Shelly candidate inspect the documented Switch.GetStatus RPC and apower field.

Use a placeholder such as METER_HOST in local instructions; keep real network details private. Confirm a permitted network path between collector and meter. If that cannot work, choose a locally logging measurement arrangement.

Verify polling/update interval, latency, coverage, stable loads, cumulative energy where supported and uncertainty. Keep only the workstation behind the measured outlet. Do not use relay-control calls during experiments.

## 6 Local configuration and credentials

The current config.yaml is historical. Before a local-only inspection set both cloud provider enabled values to false and select a small available local model. The example under docs/examples is a proposed future schema, not a drop-in runtime replacement.

Copy the credential template only when needed:

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
