# Research plan

Updated October 16, 2026. Grayson Jackson, student researcher; Rebecca Passmore, faculty mentor; UA Little Rock. The expanded scope is proposed for mentor review and must be synchronized with final application materials.

Working application title: **Energy and Privacy Tradeoffs in Local Language Models**.

## Main question

How do model size, quantization, hardware configuration, and task-specific training affect the energy required to produce useful local AI responses while keeping prompts and outputs under local control?

The motivation is concern about data-center resources and interest in retaining control of prompts and outputs. This study measures operational electricity and usefulness. It does not assume local AI is always more efficient or measure water use, manufacturing emissions or a complete environmental footprint.

## Research questions

| ID | Question | Evidence |
| --- | --- | --- |
| RQ1 | How much workstation energy does a local request use? | Synchronized wall-power trace, bounded request, model counts, idle baseline |
| RQ2 | How do model size, quantization, context and CPU offloading affect energy, quality and latency? | Paired tasks and controlled configurations |
| RQ3 | Does adaptation improve useful responses enough to justify training cost? | Held-out base/adapted comparison, training energy, amortization scenarios |
| RQ4 | What can a small randomly initialized model learn under a defined compute budget? | Learning curves, held-out loss/quality, training energy and limitations |
| RQ5 | How do local observations compare with cloud latency/cost and sourced cloud energy scenarios? | Same tasks, provider usage, dated pricing, explicit scenario boundaries |

The proposed [privacy protocol](privacy_protocol.md) documents data paths, cloud fallback, network-blocked functional tests and bounded egress observations. Privacy is a deployment property, not a fabricated numeric axis. Different local/cloud models cannot isolate a causal energy cost for privacy.

## Stages

| Stage | Scope | Status |
| --- | --- | --- |
| S0 | Audit, meter/environment validation and small pilot | Required before energy findings |
| S1 | Original 20 prompts x 2 models x 2 quantizations x 3 repeats | Original core target: 240 trials |
| S2 | Four domains x 10 prompts x 2 models x 2 quantizations x 3 repeats | Proposed expanded suite: 480 trials |
| S3 | Larger models, context, cold/warm, CPU/offload and power-setting studies | Selected controlled extensions |
| S4 | LoRA/QLoRA pilots across all four domains | Staged training extension |
| S5 | Small from-scratch language-model experiment | Exploratory extension |
| S6 | Up to two cloud endpoints | Conditional on access/budget |
| S7 | Analysis, reporting and presentations | Required outputs |

The 240-trial and 480-trial suites are different dataset versions. Their counts are not interchangeable. The existing application drafts require revision for the new training scope before submission.

## Four domains

Student priority: coding, general questions, technical documentation, then digital forensics. Representative uses are small programs, general questions and source-grounded implementation guides.

- Coding: short functions, debugging, explanations and isolated correctness checks.
- Technical document questions: source-grounded answers and summaries with claim-to-source checking.
- Digital forensics: synthetic logs, timelines, hashes and uncertainty-aware interpretation.
- General questions: verifiable factual and reasoning tasks plus insufficient-information cases.

Original creative-writing prompts remain historical benchmark material. They are not silently reclassified as forensic or grounded-document tests.

## Training scope

Start with one pretrained model and separate domain adapters, fixed splits, and the same unchanged base for comparison. LoRA is the first candidate; QLoRA is separate and requires a validated AMD quantization/training stack. Ollama inference support does not establish PyTorch training support.

For from-scratch work, select a small architecture after a memory/runtime pilot. Tens of millions of parameters are reasonable candidate scales to investigate, not a promised outcome. Record tokenizer, initialization, training tokens, repeated epochs, optimizer steps and device time. Keep this study separate from claims about competitive multi-billion-parameter models.

## Calendar

| Period | Work |
| --- | --- |
| October 2026 | Mentor scope review, application, quotes, funding/ownership decisions |
| Before hardware replacement | Preserve comparable RTX 3070 measurements if practical |
| January 2027 | Permitted purchases, validated environment, meter tests, run records |
| February | Pilot, original core, freeze expanded datasets and scoring |
| March | Core inference measurements and Expo registration by March 19 |
| April | Initial SEG findings at April 16 Expo and the defined SEG milestone |
| May-June | Freeze expanded task data/rubrics; four-domain measurements and cloud scenarios |
| July-August | Four-domain LoRA pilots and feasible repeats; larger inference/small scratch feasibility |
| September | Targeted repeats, general-domain regression and supported extensions |
| October-November | Analysis, report, reproducibility package, eligible presentation |
| By December 1, 2027 | Proposed SURF completion/reporting/spending end; confirm award terms |
| Spring 2028 | Intended Expo continuation presentation; no assumed funding extension |

Eight active hours weekly are planned across spring, summer and fall. Automated runtime is separate. Delays reduce optional work before compromising measurement validity.

## Decision record

Confirmed student preferences: individual project; $1,000 SEG unspent; new-only purchases; one R9700 32GB target; AM4 CPU/PSU upgrade; existing 32GB RAM/SSD retained initially; personal workstation; willingness to use stipend/match for equipment if allowed; both Expo intentions.

Pending: mentor approval of expanded scope, actual quotes, model revisions/quantizations, datasets, software stack, meter uncertainty, training feasibility, eligible travel, procurement/ownership, match and remaining institutional approvals.

## October 16 student clarification

The brief mentor meeting is complete; the full docket is for subsequent scope and supervision review. ORSP has not replied. The student has prior LoRA experience using PyTorch or Unsloth and is willing to use native Linux if needed. These do not establish AMD backend compatibility. Actual unattended job caps remain for pilots.

If expanded funding is unavailable, use the RTX 3070 and approved SEG purchases to answer the same core question on smaller models. Success requires valid traces, quality checks, documented privacy boundaries and reproducible findings, including infeasible or negative results. Freeze two supported open-weight models current at collection for the expanded study; the original model candidates remain legacy validation examples.
