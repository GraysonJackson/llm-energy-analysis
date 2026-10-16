# Hardware and funding

Planning record, October 16, 2026. Expanded equipment is not purchased. Purchases must be new. This is not purchasing authorization.

## Existing inventory

| Component | Confirmed |
| --- | --- |
| CPU | Ryzen 5 5600G, 6 cores/12 threads |
| GPU | RTX 3070; record exact model and usable VRAM in inventory |
| Board | ASRock B550 Phantom Gaming 4/ac |
| BIOS | P2.10 |
| RAM | 32GB; module layout/speed to record |
| SSD | WD_BLACK SN770 1TB, 408.8GB free when checked |
| PSU | Replacement planned; exact existing model unknown |
| Case/cooling | Verify final card, cable, cooler and PSU fit before purchase |

Keep private device identifiers/location in local inventory.

## Upgrade targets

| Item | Target | Rationale/check |
| --- | --- | --- |
| GPU | One AMD Radeon AI PRO R9700 32GB | Larger-model and adaptation studies; verify ROCm/Ollama/PyTorch support and memory |
| CPU | Ryzen 9 5900XT | Preparation/tokenization and CPU/offload comparison; firmware and cooling |
| PSU | Quality 850W ATX 3.1, native 12V-2x6 | Appropriate connector/headroom; exact quote/model needed |
| Cooling | Compatible CPU cooler and airflow | Stable long experiments; CPU cooler sold separately |
| Meter | Validated wall meter; Shelly Plug US Gen4 candidate | Local logging, API, update interval and uncertainty |
| RAM/storage | Retain existing capacity initially | Expand only when a measured workload justifies it |
| API | Limited usage on up to two endpoints | Public/synthetic-task quality, latency and cost comparisons |

AMD specifies R9700 32GB, 300W board power and 750W minimum PSU recommendation. The ASRock Creator uses 12V-2x6. Proposed 850W is a planning choice; PSU capacity is not measured system draw.

ASRock lists 5900XT support on this board with BIOS P3.41. Current P2.10 does not establish support. Follow exact board firmware instructions/prerequisites before replacing the CPU and record final firmware.

The primary graphics slot runs Gen3 x16 with Cezanne and Gen4 x16 with Vermeer. The second full-length slot is Gen3 x4. One R9700 is the primary plan; a second card would need a separate scoped decision and does not create automatically unified memory. The board has one storage M.2 socket.

The original SEG list had an RTX 5060 Ti 16GB at historical July prices. It remains history; obtain revised approval where required for the AMD plan.

## Funding categories

| Category | Amount | Status |
| --- | ---: | --- |
| Existing SEG | $1,000 | Awarded/unspent; original purchases approved according to student |
| SURF student stipend | $1,250 | Proposed |
| SURF mentor project costs | $750 | Proposed; allowable classification pending |
| SURF student travel | Up to $750 | Actual eligible event/costs needed |
| SURF share excluding match | Up to $2,750 | Stipend + mentor costs + justified travel |
| Institutional stipend match | $1,250 | Authorization pending |
| SURF plus match | Up to $4,000 | Includes travel; not an equipment allowance |
| Combined with SEG | Up to $5,000 | Includes travel and conditional awards |

The student wants to devote the full $2,500 stipend/match to equipment if permitted after disbursement. With SEG and proposed mentor costs that gives a conditional $4,250 non-travel target. Official entries stay stipends. Personal retention of parts is requested, not approved.

## Current review allocation

Checked October 16, 2026: Newegg displayed the ASRock R9700 CT 32GB at **$1,699.99**, sold and shipped by Newegg with Add to cart shown. This replaces the old $2,950 GPU allowance. It is a dated retail reference, not an institutional quote or guaranteed future availability.

The current review request is $1,250 student stipend plus $750 mentor costs and $0 travel: **$2,000 SURF**, **$3,250 including proposed match**, and **$4,250 including existing SEG**. Stipends remain support for research time. Their possible use for purchases is conditional.

| Item | Total USD | SEG | Mentor | Student stipend | Match |
| --- | ---: | ---: | ---: | ---: | ---: |
| One R9700 32GB | 1,699.99 | 0 | 250 | 1,250 | 199.99 |
| Ryzen 9 5900XT | 300 | 300 | 0 | 0 | 0 |
| 850W PSU | 250 | 0 | 250 | 0 | 0 |
| Cooling | 100 | 100 | 0 | 0 | 0 |
| Meter | 50 | 50 | 0 | 0 | 0 |
| API usage | 200 | 0 | 200 | 0 | 0 |
| Tax/shipping | 200 | 150 | 50 | 0 | 0 |
| Allocated total | 2,799.99 | 600 | 750 | 1,250 | 199.99 |

Except for the dated GPU listing, these are allowances or spending ceilings, not quoted costs. Obtain exact new-stock SKUs and actual destination charges. No second GPU, RAM or SSD is proposed initially.

This allocation leaves $400 of SEG without a revised expense assignment and $1,050.01 of the institutional stipend match outside the purchase list. That match remains proposed support for research time, not an additional equipment expense. Unassigned SEG must follow its award terms. Do not fabricate expenses to exhaust a ceiling.

Invoice splitting across institutional/personal funds and personal retention still need an approved process. If expanded funding is unavailable, retain the RTX 3070, use approved SEG purchases for reliable metering and needed support, and reduce optional model/training scale. No extra personal contribution is assumed.

The older $750 travel split is withdrawn from this review version. The campus Expo is free and does not justify those costs. Confirm an eligible SURF dissemination venue with ORSP; zero travel does not remove the presentation requirement. Spring 2028 dissemination does not extend the 2027 spending/reporting period.

## ORSP decisions

- Stipend/match use, disbursement, procurement and reimbursement.
- Ownership/title and retention for parts installed in a personal workstation.
- Allowable mentor-cost classification for components/API.
- Source and authorization of institutional match.
- SEG stacking, other-funding/cost-sharing treatment, revised purchases and spring deliverable.
- Eligible travel and award-period rules.

For quotes record SKU/model, vendor, new-stock condition, date/expiry, quantity, price, tax, shipping, availability, compatibility evidence, funding split and approval. A sold-out listing or MSRP is not an obtainable quote.

## Sources

- [AMD R9700](https://www.amd.com/en/products/graphics/workstations/radeon-ai-pro/ai-9000-series/amd-radeon-ai-pro-r9700.html)
- [ASRock R9700 Creator](https://www.asrock.com/Graphics-Card/AMD/Radeon%20AI%20PRO%20R9700%20Creator%2032GB/)
- [AMD 5900XT](https://www.amd.com/en/products/processors/desktops/ryzen/5000-series/amd-ryzen-9-5900xt.html)
- [Motherboard specification](https://pg.asrock.com/mb/AMD/B550%20Phantom%20Gaming%204ac/index.asp)
- [CPU support](https://www.asrock.com/support/cpu.asp?s=AM4&u=769)
- [SURF](https://sams.adhe.edu/Scholarship/Details/SURF)
- [ORSP purchasing](https://ualr.edu/orsp/award-management/)
- [SEG guidelines](https://ualr.edu/signature/award-guidelines/)

- [Dated GPU retail reference](https://www.newegg.com/asrock-creator-r9700-ct-radeon-ai-pro-r9700-32gb-graphics-card/p/N82E16814930143)
