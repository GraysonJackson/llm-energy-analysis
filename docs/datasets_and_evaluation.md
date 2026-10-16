# Datasets and evaluation

This document specifies the four-domain extension and its training/evaluation records. Existing data/prompts.json is the immutable legacy v1 suite until deliberately versioned. The new domain suite and training data are not yet implemented.

## Dataset versions and counts

| Suite | Content | Initial target |
| --- | --- | --- |
| legacy-v1 | Existing 20 prompts across original five categories | 240 local trials for 2 models x 2 quantizations x 3 repeats |
| domains-v2-pilot | Two evaluation tasks per domain | 16 attempts at one condition and two repeats |
| domains-v2 | Coding, document questions, forensics, general questions | 10 tasks/domain = 40; 480 local trials for 2 x 2 x 3 |
| domain-training-pilot | Separate training examples per domain | Proposed 100-300 checked examples/domain |
| domain-validation | Separate source groups for tuning decisions | Size chosen and frozen with corpus |
| domain-test | Frozen held-out final tasks | Never used to select prompts/hyperparameters |

These are design targets, not completed records or guarantees of statistical sufficiency. The training pilot may use fewer examples to debug before any scientific run.

## Sources and permissions

Each source needs source_id, title/origin, author or generator, URL when public, retrieval date, license/permission, content hash, source_group_id and permitted uses. Synthetic material records its generator/version and independent ground-truth review.

Choose authored synthetic tasks, public-domain content or sources with explicit compatible permissions. A dataset being downloadable does not establish training/redistribution rights. Model licensing is separate from dataset licensing.

Store restricted/downloaded corpora outside Git. Commit small authored fixtures, manifests without private identifiers, dataset-building code and approved summaries. Do not place real investigation evidence, student records, personal logs or credentials into prompts.

## Source-aware splitting

1. Normalize source material without destroying meaningful code/log layout.
2. Assign stable source groups before generating examples.
3. Detect exact duplicate normalized hashes.
4. Check near duplicates, paraphrases and shared templates manually or with a documented similarity method.
5. Split source groups, then create derivative examples only inside their assigned split.
6. Keep all questions about one held-out document/log scenario in the same split.
7. Fit tokenizer/preprocessing/retrieval components on allowed training material only when applicable.
8. Freeze split manifests and hashes.
9. Audit item/source/domain counts and exclusions.
10. Start a new dataset version if evaluation content or scoring meaning changes.

An 80/10/10 group split can be a candidate when enough independent groups exist; it is not meaningful for tiny data. Select explicit independent validation/test groups in a small pilot and report limited coverage.

## Record format

Fields for each item:

| Field | Use |
| --- | --- |
| item_id | Stable unique identifier |
| dataset_version, split | Immutable provenance |
| domain, task_type | Category and actual operation |
| difficulty | Prespecified descriptive tier |
| source_group_id, source_ids | Leakage/control grouping |
| input/context | What the model may see |
| expected_answer/evidence | Evaluation-only target |
| scoring_rule_id/version | Exact rubric/checker |
| answerable | Whether supplied evidence supports an answer |
| constraints | Length, format, language, permitted context |
| license/permission | Permitted use |
| content_hash | Detect unintended changes |
| reviewed_by/status | Ground-truth review evidence |

The runtime prompt payload must exclude expected answers, scorer notes and hidden tests. Training examples can contain target answers, but only in the training split.

## Coding domain

### Initial evaluation coverage

Include short deterministic functions, edge-case handling, simple data transformations, SQL over a supplied schema, bug diagnosis and explanation of bounded code.

Suggested ten-task balance:
- Four function/algorithm tasks with executable tests.
- Two bug-fix tasks.
- Two data/SQL tasks.
- Two explanation tasks.

This is a proposed design. Preserve item IDs and exact tests when frozen.

### Example task

Input: implement a function returning the first index of a target in a sorted integer list or -1 if absent.

Hidden checks: empty input, singleton, absent target, first/last positions, negative integers and repeated targets.

Score functional correctness using reviewed tests and record pass count/total. Score adherence separately, including signature/output format and requested explanation.

Generated code executes only in a disposable restricted environment with no credentials or network, finite CPU/memory/time and controlled filesystem access. A normal subprocess timeout is not a sandbox. Review isolation before enabling automatic execution.

### Training examples

Use small reviewed problem/solution pairs or code-edit examples from approved sources. Keep related problem families and paraphrases together during splitting. Do not train on held-out hidden tests.

## Technical document questions

### Coverage

Provide the source passage in the prompt unless retrieval is the experiment. Include extraction, multi-section synthesis, procedure questions, concise summaries and explicit no-answer cases.

Suggested ten tasks: six answerable questions, two constrained summaries and two questions unsupported by the document.

Score factual claims against specific supplied passages. Require source identifiers or passage references when the task requests them. Do not reward plausible external knowledge that the task required to be grounded in the supplied source.

### Example

Synthetic service manual:
- Service writes a status record every 30 seconds.
- Restart after a missing heartbeat requires checking storage availability first.
- Manual gives no procedure for credential rotation.

Answerable: what should be checked before restart?
Unanswerable: how often does the manual require rotating credentials?

Expected behavior: answer the first from the text; state that the second is not specified.

### Retrieval extension

RAG is optional. Keep provided-context evaluation separate from retrieval-plus-generation. Record document index/hash, retriever, embedding model, retrieval settings, retrieved passage IDs and retrieval energy. Never attribute retrieval improvements solely to model training.

## Digital forensics domain

### Coverage

Use synthetic logs and authored evidence descriptions for:
- Event ordering with UTC/time-zone information.
- Hash equality and its limited implications.
- File metadata interpretation.
- Distinguishing observation from inference.
- Identifying missing evidence and avoiding unsupported attribution.
- Concise report summaries grounded in provided artifacts.

Suggested ten tasks: three timelines, two hash/metadata tasks, three evidence-interpretation tasks and two insufficient-evidence cases.

### Example

Synthetic events: successful login at 10:00Z; file creation at 10:02Z; hash collected at 10:05Z. No process execution event is supplied.

Questions: order the observations and state whether the evidence establishes which process created the file.

Expected behavior: correct order and explicit inability to identify a process from the supplied records alone.

Avoid tasks requiring actual malware execution. This energy study does not require detonation, exploit execution or real case access.

### Scoring

Check correct event order, time-zone conversion, source/evidence citations, hash reasoning, uncertainty and absence of invented artifacts. A confident attribution unsupported by evidence fails the relevant criterion.

## General-question domain

### Coverage

Use frozen, verifiable factual questions, bounded reasoning, arithmetic with explicit units, explanation and insufficient-information questions. Keep external current events out unless a dated source is supplied.

Suggested ten tasks: four factual/explanatory, four reasoning/arithmetic and two ambiguous/unanswerable cases.

Check arithmetic independently. Define units, rounding and whether multiple interpretations are acceptable. Annotate ambiguous items before collection rather than changing the answer key to match model output.

General-domain tasks also form a regression check for each domain adapter. A specialized quality gain can coexist with worse general performance.

## Proposed scoring rubric

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Correctness | Materially wrong | Partly correct with meaningful error | Correct for task |
| Completeness/adherence | Missing essential request | Minor omissions | Meets requested content/format |
| Grounding/evidence | Invented/contradicted evidence | Partly supported or weak references | Supported, appropriately attributed |
| Uncertainty | Unsupported certainty or inappropriate refusal | Mixed handling | Calibrated answer/abstention |

Use only applicable dimensions. Coding executable correctness remains a separate numeric check. Do not treat scores across unrelated rubrics as an absolute common scale.

Before collection define critical failures and adequacy. A candidate policy is no critical error plus full correctness and at least acceptable adherence/evidence. Select and freeze the actual policy with mentor review. Report per-dimension scores and adequacy, not only a combined total.

## Evaluation procedure

1. Score baseline and adapted outputs against identical held-out items.
2. Hide model/condition labels for manual review when practical.
3. Save raw output, checker evidence and scoring explanation.
4. Re-score a sample later; ask mentor to review a subset when available.
5. Resolve/disclose disagreement without editing raw outputs.
6. Keep failures, truncated outputs and unsupported claims.
7. Report quality and energy for all attempts and adequate outputs separately.
8. Version scoring changes and rerun affected summaries.

A model judging itself is not independent ground truth. An optional external model judge needs a fixed rubric, version, bias checks, private-data review and separate cost/usage accounting.

## Adaptation evaluation

For every adapter record base revision, domain, training seed/method and training data hashes. Evaluate:
- Target-domain quality and adequacy.
- General-domain regression.
- The other domains where useful to assess transfer.
- Output length, latency and electricity.
- Training-job and campaign energy.

If comparing a smaller adapted model with a larger pretrained model, keep the size difference explicit. Match quality thresholds before discussing energy savings.

## Dataset completion criteria

- [ ] Sources and licenses recorded.
- [ ] Independent source groups and leakage checks complete.
- [ ] All four domains represented.
- [ ] Inputs separated from targets/checkers.
- [ ] Ground truth independently checked.
- [ ] Rubric/adequacy and splits frozen.
- [ ] Tiny fixtures and representative failure cases pass.
- [ ] Hash/version recorded in every run.
