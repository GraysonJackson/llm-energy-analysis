# Privacy and local control protocol

Proposed protocol, October 16, 2026. No privacy tests have been completed by this documentation update.

## Question and hypothesis

Which local model and configuration can meet a task's quality requirements with the least measured workstation electricity while keeping prompts and responses under local control?

The student expects smaller local models may be sufficient for many everyday tasks and may use less electricity than some cloud scenarios. This is a hypothesis. A data center serves many users; its total electricity does not establish electricity per useful answer.

The working application title is **Energy and Privacy Tradeoffs in Local Language Models**. Privacy remains a central cybersecurity motivation.

## Protected content and boundary

Document prompts, supplied task documents, generated responses, logs, caches, model artifacts and adapters. Record where each is processed and stored, who can access it and when it is removed. Use public or authored synthetic data for this study. Do not bring employer documents or real forensic case material into the benchmark.

Local control concerns where content goes. It does not establish that all local dependencies, users or services are secure.

## Verification sequence

1. Inventory the runtime, wrappers, plugins, local service bindings, telemetry settings and any fallback endpoints.
2. Download models and dependencies before the defined offline test. Freeze revisions and hashes.
3. Configure the local service for the intended local interface; avoid an unnecessarily exposed network listener.
4. Disable cloud fallback. Verify failures remain local instead of silently routing content to a provider.
5. Map the network boundary. A LAN-connected meter may remain available while external network access is blocked.
6. Run a fixed functional workload with external access blocked. Save settings, time window, expected connections and outcomes.
7. Where permitted, inspect necessary connection metadata for unexpected egress during that window. Restrict observation to this workstation and avoid collecting others' traffic.
8. Record attempted and successful connections separately. A blocked attempt is evidence of attempted egress, not absence of attempts.
9. Examine response/log/cache paths and the public export for prompts, secrets, identifiers and private paths.
10. Run deliberate cloud comparisons separately using only the approved public/synthetic tasks.

Do not publish credentials, raw captures, account details, private paths, addresses or workstation location.

## Records

For every check retain: check ID, run/condition ID, timestamp, software/config hashes, intended boundary, evidence reference, observed result, limitations and reviewer status.

Possible results are pass, fail, unavailable and not tested. Missing evidence is not a pass. A local generation success and an egress check are separate observations.

## Claims

A supported claim could describe a particular runtime completing selected tasks while external access was blocked, with processing and outputs kept on the configured machine under that tested setup.

Do not claim an air gap, universal confidentiality, immunity to malicious software or an independent security certification. Logs, dependencies, exposed services and later configuration changes remain relevant risks.

Compare electricity at matched answer adequacy. Do not fabricate a numerical privacy score or attribute an energy difference between different models solely to privacy.

## Task priorities and fallback

The priority order is coding, general questions, technical documentation, then synthetic digital forensics. Representative tasks include small programs, verifiable questions, and implementation guides grounded in supplied sources.

Keep the RTX 3070 for a measured baseline. If additional funding is unavailable, complete the smaller-model core with that GPU and approved SEG purchases. No extra personal contribution is assumed. Larger inference, QLoRA and scratch training remain conditional on measured feasibility.

See [implementation guide](implementation_guide.md), [methodology](methodology.md) and [datasets](datasets_and_evaluation.md).
