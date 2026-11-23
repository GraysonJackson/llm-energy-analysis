# Research plan

Updated October 16, 2026. Grayson Jackson, student researcher; Rebecca Passmore, faculty mentor; UA Little Rock. The expanded scope is proposed for mentor review and must be synchronized with final application materials.

Working application title: **Energy and Privacy Tradeoffs in Local Language Models**.

## Main question

What are the operational electricity and privacy tradeoffs of completing the same tasks with AI on a local workstation or through cloud AI services, at comparable task quality?

The study measures workstation electricity, evaluates task quality and latency, and reviews local and provider data handling. Cloud server electricity depends on available evidence for the selected endpoints. Model size, quantization, hardware, and training are secondary questions in the expanded proposal.

## Research questions

| ID | Question | Evidence |
| --- | --- | --- |
| RQ1 | How much workstation energy does a local request use? | Synchronized wall-power trace, bounded request, model counts, idle baseline |
| RQ2 | How do model size, quantization, context and CPU offloading affect energy, quality and latency? | Paired tasks and controlled configurations |
| RQ3 | Does adaptation improve useful responses enough to justify training cost? | Held-out base/adapted comparison, training energy, amortization scenarios |
| RQ4 | What can a small randomly initialized model learn under a defined compute budget? | Learning curves, held-out loss/quality, training energy and limitations |
| RQ5 | How do local observations compare with cloud latency/cost and sourced cloud energy scenarios? | Same tasks, provider usage, dated pricing, explicit scenario boundaries |

The proposed [privacy protocol](privacy_protocol.md) documents data paths, cloud fallback, network-blocked functional tests and bounded egress observations. Privacy is a deployment property, not a fabricated numeric axis. Different local/cloud models cannot isolate a causal energy cost for privacy.

## Local and cloud comparison

Decisions recorded November 22, 2026. The comparison uses Gemma 4 12B, GPT-OSS 20B, and Qwen 3.8 27B on the RTX 5060 Ti workstation. The two cloud candidates are GPT-6.2 Sol and Claude Sonnet 5.5. Target every task on both providers within a $10 USD research API spending cap per provider.

- **Direct answers:** Standalone coding, email and workplace writing, document Q&A, summarization, structured extraction, general reasoning, and synthetic defensive log analysis. Use public or authored synthetic text, with a mix of difficulty levels.
- **Agentic coding:** Primarily Python tasks covering bug fixes, features, tests, code understanding, refactoring, and setup. Each model starts from the same repo snapshot in a fresh workspace with the same offline tools and limits.
- **Fair comparison:** Pair results by task ID and give each model the same task and starting materials within its track. Use one shared context limit and record CPU/GPU placement. Report scores by category and track. Score runnable coding tasks against hidden tests and use task-specific rubrics for subjective work. Review a sample with the mentor where possible.
- **Measurement:** Record no-model workstation idle first. The warm-run comparison also uses matched idle baselines. Meter the workstation for both local and cloud modes, including tool and test execution. Report pass rate, time to completion, and energy per adequate task with failed attempts included in the energy total. Research server energy separately.
- **Scale:** Begin with the 12 paired pilot tasks. Target 60–80 distinct evaluation tasks and three local repetitions. Freeze final tasks and scoring rules after the pilot. Give both cloud providers one pass across all tasks first. Use remaining budget for repeats on a preselected, category-balanced subset shared by both providers.
- **Privacy:** Compare observed local data paths and documented first-party API data handling in the main analysis. Include a separate appendix on consumer ChatGPT and Claude privacy settings and policies.

The [methodology](methodology.md) governs energy measurements and records the cloud evidence search. The [privacy protocol](privacy_protocol.md) governs data-flow observations and provider research. See [the pilot instructions](datasets_and_evaluation.md#paired-pilot-v1) for the draft tasks, scoring keys, and provisional run limits. Pilot validation will inform the final time and context limits.

## Earlier proposal stages

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

The 240-trial and 480-trial suites are different dataset versions. Their counts are not interchangeable. The private application drafts reflect the staged scope; student and mentor must finalize them before submission.

## Four domains in the earlier proposal

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

## Readiness after October 23 funding guidance

The brief mentor meeting is complete and the mentor has given positive feedback on the docket, requesting the PAR separately. This does not establish completion of institutional routing or detailed approvals. ORSP clarified student stipends through financial aid, mentor-selected payment scheduling, and presentation-only travel. Exact mentor-item classifications, institutional match authorization, net stipend availability and Foundation SEG decisions remain pending. The student has prior LoRA experience using PyTorch or Unsloth and is willing to use native Linux if needed. These do not establish AMD backend compatibility. Actual unattended job caps remain for pilots.

If expanded funding or sufficient net stipend cash is unavailable, use the RTX 3070 and approved SEG purchases to answer the same core question on smaller models. Success requires valid traces, quality checks, documented privacy boundaries and reproducible findings, including infeasible or negative results. Freeze two supported open-weight models current at collection for the expanded study; the original model candidates remain legacy validation examples.
