# Privacy and local control protocol

Protocol first drafted October 16, 2026. Provider documentation reviewed November 22, 2026. Local observation and actual API account settings still need verification.

## Question and hypothesis

What happens to prompts, outputs and related data when the same task runs on this workstation or through one of the two cloud providers?

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

## Provider policy review

The main comparison uses the first-party APIs. For each request record which data classes the harness sends, including prompt text, conversation context, tool definitions and selected file or command results. The dedicated coordinator makes provider calls while agent workspaces run with networking disabled. A cloud agent's tests can execute locally while their output is sent to a provider in the next request. Record that transfer as part of the cloud task.

| Endpoint | Provider policy snapshot | What to verify before the study |
| --- | --- | --- |
| OpenAI Responses, `gpt-6.2-sol` | API content is excluded from training by default unless the customer opts in. Standard abuse-monitoring logs can contain prompts, responses and derived metadata, usually retained up to 30 days subject to exceptions. Responses can also retain application state. [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data) | Record the project data-sharing and retention settings. Use foreground Responses and set `store: false`. Document any caching or tools actually enabled. Treat application state and abuse monitoring as separate. |
| Anthropic Messages, `claude-sonnet-5-5` | Commercial API input and output are excluded from training by default. Standard API input and output are generally deleted within 30 days, with exceptions for selected features, agreements, usage-policy enforcement and legal requirements. [Commercial training policy](https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training) · [Commercial retention policy](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data) | Record the actual workspace controls. Use the Messages API and shared local tools. Record caching and any provider feature enabled. The analysis should assume standard terms until a different arrangement is confirmed. [Anthropic API retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) |

Save dated sources and record policy revisions, applicable account and region, configured controls, declared purposes, retention exceptions and any evidence of actual data transfers. Distinguish content, account/usage metadata and derived logs. Label each finding as a provider statement, an observed request or local behavior, or an unresolved question. Observing what we send cannot verify deletion on provider systems.

## Records

For every check retain: check ID, run/condition ID, timestamp, software/config hashes, intended boundary, evidence reference, observed result, limitations and reviewer status.

Possible results are pass, fail, unavailable and not tested. Missing evidence is not a pass. A local generation success and an egress check are separate observations.

## Claims

A supported claim could describe a particular runtime completing selected tasks while external access was blocked, with processing and outputs kept on the configured machine under that tested setup.

Do not claim an air gap, universal confidentiality, immunity to malicious software or an independent security certification. Logs, dependencies, exposed services and later configuration changes remain relevant risks.

Compare electricity at matched answer adequacy. Do not fabricate a numerical privacy score or attribute an energy difference between different models solely to privacy.

## Current comparison setup

The paired task suite and RTX 5060 Ti workstation are documented in the [research plan](research_plan.md). Keep any previous RTX 3070 measurements labeled as a historical hardware condition.

See [implementation guide](implementation_guide.md), [methodology](methodology.md) and [datasets](datasets_and_evaluation.md).

## Appendix: Consumer ChatGPT and Claude

Use these comparisons to explain what changes when someone uses the consumer chat interface. The benchmark uses APIs, so report consumer notices and controls here separately. This is a policy review with no consumer sessions or account settings inspected.

| Consumer service | Data and controls to document |
| --- | --- |
| ChatGPT | OpenAI's U.S. policy covers content such as prompts and uploads, account information, device and usage data, and approximate location inferred from an IP address. Training controls apply to consumer chats. Temporary Chat excludes conversations from model improvement and history, with a copy potentially retained for up to 30 days for safety. Third-party actions have their own data handling. [Privacy policy](https://openai.com/policies/privacy-policy/) · [Data controls](https://help.openai.com/en/articles/7730893-data-controls-faq) · [Temporary Chat](https://help.openai.com/en/articles/8914046-temporary-chat-in-chatgpt) |
| Claude | Anthropic's individual policy covers prompts and supplied content, account and usage data, and technical information. Model Improvement controls whether personal chats and coding sessions can be used for training. Opted-in content may be held in de-identified form for up to five years in training pipelines. Anthropic says Incognito chats are excluded from model improvement. Retention, safety review and feedback have their own policies and exceptions. [Privacy policy](https://www.anthropic.com/legal/privacy) · [Consumer retention](https://privacy.claude.com/en/articles/10023548-how-long-do-you-store-my-data) · [Consumer training controls](https://privacy.claude.com/en/articles/10023580-is-my-data-used-for-model-training) |
