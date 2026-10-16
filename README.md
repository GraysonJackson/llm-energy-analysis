# LLM Energy Analysis

This project investigates how model size, quantization, hardware configuration, and task-specific training affect the electricity required to produce useful local AI responses. It compares measured workstation energy with clearly identified cloud energy estimates or scenarios. Local inference is not assumed to be more efficient, and local hosting alone is not a security guarantee.

Grayson Jackson is the student researcher at the University of Arkansas at Little Rock. Rebecca Passmore is the faculty mentor. A $1,000 Signature Experience Grant has been awarded and remains unspent as of October 16, 2026. The expanded SURF application and equipment allocation are being prepared; they are not an awarded SURF budget.

## Start here

| Document | Contents |
| --- | --- |
| [Documentation index](docs/README.md) | Reading order and document authority |
| [Research plan](docs/research_plan.md) | Questions, stages, four task areas and milestones |
| [Implementation guide](docs/implementation_guide.md) | Detailed build order, contracts, experiments, validation and acceptance criteria |
| [Methodology](docs/methodology.md) | Measurement boundaries, calculations, controls and interpretation |
| [Datasets and evaluation](docs/datasets_and_evaluation.md) | Data preparation, held-out splits, scoring and examples |
| [Hardware and funding](docs/hardware_and_funding.md) | Existing equipment, AMD target, conditional allocations and purchasing decisions |
| [SURF preparation](docs/surf_preparation.md) | Public-safe application status and outstanding decisions |
| [Setup guide](docs/setup_guide.md) | Inspecting the scaffold and preparing a validated environment |
| [Legacy API reference](docs/api_documentation.md) | Existing interfaces, with corrections and limitations at the top |

## Research stages

1. Validate measurement and reproduce a small inference pilot.
2. Complete the original two-model, two-quantization, 20-prompt core benchmark: 240 local trials at three repetitions.
3. Extend to coding, technical document questions, digital forensics and general questions. The proposed 40-prompt suite has 480 local trials and is versioned separately.
4. Compare larger existing models that actually fit the upgraded system.
5. Pilot LoRA/QLoRA fine-tuning across all four task areas, measuring training cost and subsequent inference behavior.
6. Investigate a small language model trained from scratch as an exploratory extension.
7. Compare local latency, usage and quality with up to two cloud endpoints. Cloud server electricity remains an estimate or scenario.

Training and the expanded experiment system are proposed work, not already implemented features. The original baseline remains useful if a later stage cannot pass its feasibility checks.

## Hardware

| Component | Existing baseline | Proposed upgrade |
| --- | --- | --- |
| GPU | RTX 3070 | One new AMD Radeon AI PRO R9700 32GB |
| CPU | Ryzen 5 5600G | New Ryzen 9 5900XT, subject to BIOS support |
| Motherboard | ASRock B550 Phantom Gaming 4/ac, BIOS P2.10 | Retain; verify CPU update path |
| RAM | 32GB | Retain initially; measure additional training need |
| SSD | WD_BLACK SN770 1TB, 408.8GB free when checked | Retain initially |
| PSU | Replacement needed | Quality 850W ATX 3.1 target with appropriate native connector |
| Meter | Still needed | Validated wall-power meter; Shelly candidate |

These are targets, not purchased equipment. A 32GB GPU does not guarantee arbitrary model sizes, context lengths or training methods.

## Current implementation status

The Python files are a starting scaffold. No validated benchmark results are committed. Before research collection:

- Collect continuous power samples during generation. The current local path starts/stops a session without sampling it.
- Replace approximate local token counts with runtime-reported counts.
- Retain and use the configured Ollama client.
- Calculate incremental energy using an explicit matched baseline.
- Replace historical cloud prices and unsupported fixed energy factors with dated sources or unavailable values.
- Preserve outputs/errors for quality review; current CSV exports discard important fields.
- Select results by run manifest rather than independently selecting newest files.
- Revise plots/report wording that implies measured cloud energy or predetermined privacy-energy conclusions.
- Implement dataset splits, training, scoring, manifests, resume logic and the expanded matrix.

The implementation guide describes fixes and verification. This documentation update does not change runtime code.

## Inspect the scaffold

From the repository root:

~~~bash
python -m venv .venv
~~~

Activate with `source .venv/bin/activate` on Linux or `.venv\Scripts\Activate.ps1` in PowerShell, then:

~~~bash
python -m pip install -r requirements.txt
python -m compileall -q src reports
~~~

Dependencies have broad minimum versions. Record a tested environment before research runs. These commands inspect the scaffold; they do not validate measurements. The checked-in `config.yaml` remains a legacy configuration with historical model IDs and unsupported energy assumptions. Read the setup guide before running hardware or cloud scripts.

## Schedule and outputs

- Proposed SURF period: January 1 through December 1, 2027; eight active hours weekly during spring, summer and fall, with automated runtime tracked separately.
- Initial SEG findings: spring 2027 Expo. Published date April 16; registration closes March 19.
- Complete SURF work/reporting within the approved period, proposed to end December 1, 2027.
- Intended follow-up: spring 2028 Expo, details pending. This does not extend the 2027 funding period.

Outputs include traceable measurements, response-quality evaluation, analysis scripts, uncertainty statements and presentations. Failed configurations and negative findings remain part of the record.

## Research records

Commit code, public documentation, synthetic fixtures and approved summaries. Keep credentials, signed forms, transcripts, recommendation letters, private contact records, large model weights and raw run artifacts outside Git. Review licenses before publishing datasets or adapters.

The repository does not currently declare a software license. An academic-purpose statement is not a substitute for choosing one.
