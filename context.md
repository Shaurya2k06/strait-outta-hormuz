# Quantiz’26 “Strait Outta Hormuz” — Case Context

## Purpose

This file is the self-contained case and data reference for the War Room Masterplan. It captures the official question, the commercial logic, the supplied data definitions, the known hazards, the five strategic tensions, and the evidence standard. A reader should not need to re-read the case PDF before beginning analysis.

Status labels used below:

- **FACT:** stated in the supplied case or data dictionary.
- **DERIVED:** calculated from the supplied cleaned workbook.
- **PROPOSAL:** an analytical or decision rule to test, not an official case fact.
- **OPEN CONTROL:** unresolved evidence that must be closed before presentation numbers are frozen.

## The board’s real question

**FACT:** The Hormuz disruption made a historically efficient shipment network more expensive and less predictable. Management does not want an affected-shipment list, an exhaustive route ranking, or the single “worst” route. It wants a decision-ready answer to:

> Where are we most exposed, where does that exposure become a business problem, and what should the company protect, change, or stop doing before the next disruption?

The answer must connect three levels:

1. **Operational:** what changed in routes, transit, service performance, and cost-to-serve?
2. **Commercial:** which customers and products absorb the impact when contracted freight revenue is fixed?
3. **Strategic:** which exposures should be accepted, renegotiated, mitigated, diversified, insured differently, or exited?

The governing causal chain is:

**Hormuz shock → operating vulnerability → commercial transmission → dollars/service at risk → differentiated action and trigger**

## Situation and commercial model

**FACT:** The company serves multiple customers, regions, and product categories. Before the blockade, the Direct route through Hormuz was the efficient corridor. During the disruption, shipments were rerouted through the Cape of Good Hope, Pipeline Bypass, Overland Truck, or Air Bridge, while others remained Held in Gulf.[^1]

**FACT:** Contracted freight revenue was negotiated before the blockade and is largely fixed. Actual cost-to-serve varies with the route used, fuel, insurance, and delay penalties. Higher logistics cost therefore cannot be assumed recoverable through price.

This creates the central commercial mechanism:

`Fixed contracted freight revenue − changed cost-to-serve = margin compression or loss`

Operational feasibility is not enough. A route may deliver but destroy contribution; an expensive route may still be justified for a time-critical product or strategic account; and a high-revenue shipment may be commercially unattractive after cost, insurance, delay, and service consequences.

## Supplied files and observation window

| Item | Supplied information |
| --- | --- |
| Case document | `R2-War Room Masterplan Case Study(1).pdf`, 7 pages |
| Data workbook | `R2-WAR ROOM MASTERPLAN-cleaned(1).xlsx` |
| Period | 5 January to 22 March 2026 |
| Workbook sheets present | `Shipment_Data`; `Data_Dictionary_Enriched` |
| Columns | 29 |
| Case-stated record count | 246 shipment records |
| Cleaned-workbook record count | 243 rows and 243 unique `Shipment_ID`s |

### Open source control

**OPEN CONTROL:** The case says there are 246 records and that duplicate `Shipment_ID`s are intentionally present. The uploaded cleaned workbook contains 243 rows, 243 unique IDs, and no duplicates. It also lacks several supporting sheets described in the PDF.

The likely explanation is an upstream cleaned/source-version difference, but this must not be treated as proven. Do not prorate the 243-row totals to 246 or manufacture missing rows. Before final submission:

1. obtain or reconcile the referenced 246-row workbook;
2. compare all columns within each repeated `Shipment_ID`;
3. collapse an exact duplicate row once;
4. stop and adjudicate any conflicting duplicate ID;
5. assert one surviving row per ID before every count, sum, share, rate, score, or chart; and
6. rerun every headline, rank, threshold crossing, and scenario.

Current calculated amounts are **provisional working controls** for the supplied cleaned workbook.

## Route and status states

| Route/status | Meaning | Analytical treatment |
| --- | --- | --- |
| Direct (Pre-Blockade) | Historical Hormuz route used before 1 February 2026 | Benchmark/reference only. It is not assumed available after the disruption. |
| Cape of Good Hope | Longer maritime reroute | Delivered route. Compare only within feasible cargo/product sets and against route-specific plans. |
| Pipeline Bypass | Alternative observed only for bulk liquids | Delivered route. Do not infer capacity or destination equivalence from observation alone. |
| Overland Truck | Alternative observed only for containers | Delivered emergency route. Interpret economics under the fixed ocean-rate contract caveat. |
| Air Bridge | Alternative observed for High-Tech and Pharmaceuticals | Delivered emergency route. Interpret economics under the fixed ocean-rate contract caveat. |
| Held in Gulf | Trapped and undelivered as of 22 March 2026 | Open-exposure status, not a completed route. `Actual_Transit_Days` is unavailable and must not be imputed. |

## Provisional portfolio controls

All figures in this section are **DERIVED** from the 243-row cleaned workbook.[^2]

| Control | Working value |
| --- | ---: |
| Unique shipments | 243 |
| Direct pre-blockade | 51 |
| Post-blockade delivered | 138 |
| Held in Gulf | 54 |
| Total post-blockade rows | 192 |
| Contracted freight revenue | $113.313m |
| Revenue recognized | $87.389m |
| Held contracted but unrecognized revenue | $25.924m |
| Total cost-to-serve | $277.009m |
| Gross margin accounting result | -$189.620m |
| Post-blockade signed route sensitivity | $177.481m |
| Post-blockade positive-only adverse sensitivity | $178.710m |
| Favorable sensitivity offsets | -$1.228m |
| Direct delivered DIFOT | 51/51 = 100.0% |
| Post-blockade delivered DIFOT | 113/138 = 81.9% |

### Held-in-Gulf control pool

| Held measure | Working value |
| --- | ---: |
| Shipments | 54 |
| Contracted but unrecognized revenue | $25.924m |
| Cost accrued to date | $34.315m |
| Penalties | $26.016m |
| Insurance | $4.481m |
| Cumulative days stuck | 1,234 |
| Median days stuck | 20.5 |
| Maximum days stuck | 47 |

Held shipments are not assigned a delivered DIFOT rate or realized delivered margin. Their `DIFOT_Met = N` source value indicates they are not delivered, but they are excluded from delivered-route denominators. Their risk is open revenue, cost accumulation, service failure, and queue aging.

## Provisional concentration and exposure findings

### Dollar materiality

- Meridian, Zenith, and Pacific account for **90.4%** of post-blockade positive route-sensitivity exposure.
- Pipeline Bypass and Cape of Good Hope account for **92.3%** of post-blockade positive route-sensitivity exposure.
- Crude Oil and Refined Petrochemicals account for **99.1%** of post-blockade positive route-sensitivity exposure.
- Meridian and Zenith account for **81.0%** of Held contracted revenue.

### Customer concentration

Customer concentration must be recomputed from unique shipments:

`Customer share = customer contracted freight revenue ÷ $113,313,425.66 unique-portfolio contracted revenue`

| Customer | Recomputed portfolio share |
| --- | ---: |
| Meridian Energy Partners | 58.34% |
| Zenith Crude Traders | 20.04% |
| Pacific Rim Petrochem | 8.14% |
| Baltic Fuel Alliance | 6.50% |
| Nordholm Refining Group | 5.47% |

The stored concentration field differs by as much as 0.761 percentage points because it reflects the unreconciled raw source. It is a QA clue, not an authoritative headline measure.

### Exposure Score working results

The score is a whole-number, within-universe ordinal priority index. It is not a probability, dollar VaR, forecast, or expected loss. Raw dollars must always appear beside it.

| Universe | Leading working results |
| --- | --- |
| Customer | Pacific 85; Baltic 80; Nordholm 70; Zenith 70; Meridian 61. Meridian remains the largest dollar exposure despite ranking fifth on rate/vulnerability severity. |
| Route/status | Pipeline 71; Cape 64; Held 56; Air 45; Overland 14. Held remains a mandatory override regardless of rank. |
| Product | Refined Petrochemicals 83; Crude Oil 60; High-Tech 49; Industrial Machinery 47; Pharmaceuticals 41; Consumer Goods 20. |

## Data dictionary and decision cautions

| Column | Official meaning | Decision use / hazard |
| --- | --- | --- |
| `Shipment_ID` | Shipment/voyage identifier | Canonical record grain and duplicate QA key. Never aggregate until uniqueness is resolved. |
| `Departure_Date` | Departure date | Defines the observation window and supports aging/cohort checks. Do not infer seasonality from 77 days or ignore right-censoring near 22 March. |
| `Route_Type` | Direct, Cape, Pipeline, Overland, Air, or Held | Primary operating state and action lever. Direct is benchmark-only; Held is a status, not a completed route. |
| `Product_Category` | Six product groups | Required for product-specific Direct benchmark, cargo physics, criticality, and product-route action. |
| `Cargo_Type` | VLCC, chemical tanker, or container | Feasibility guardrail. It is determined by product in this file, so it is not a separate headline segmentation. |
| `Customer_Name` | Contracting customer | Commercial action owner/grain and concentration dimension. |
| `Customer_Region` | Customer home region | Context only. It is not shipment origin, destination, lane, or contract jurisdiction. |
| `Customer_Since` | Relationship start year | Weak context only. It does not establish lifetime value, renewal risk, or strategic importance. |
| `Cargo_Weight_Tons` | Cargo weight | Denominator for rate normalization. Aggregate tonnes before dividing. |
| `Cargo_Value_USD` | Market value of goods | Insurance denominator and goods-at-risk context. It is not company revenue. |
| `Contracted_Freight_Revenue_USD` | Fixed shipping fee | Commercial value, concentration denominator, and Held backlog value. |
| `Planned_Transit_Days` | Expected transit for route used | Service denominator. Compare actual against the route-specific plan. |
| `Actual_Transit_Days` | Completed transit time | Delivered shipments only; blank by design for Held. Never impute Held values. |
| `Delay_Days` | Actual minus planned for delivered; days stuck for Held | Two meanings. Keep delivered delay and Held aging separate. |
| `Freight_Cost_USD` | Physical freight cost component | Financial bridge component only; already included in total cost. |
| `Fuel_Cost_USD` | Fuel cost component | Financial bridge/scenario component only; already included in total cost. |
| `Insurance_Cost_USD` | Voyage insurance cost | Dollar input for re-insure decision. Aggregate burden as insurance ÷ cargo value. |
| `Penalty_Cost_USD` | Contractual delay/DIFOT penalty | Monetizes service failure. It does not capture all relationship or working-capital consequences. |
| `Total_Cost_to_Serve_USD` | Freight + fuel + insurance + penalty | Authoritative current cost and bridge control. Do not add its components again. |
| `Revenue_Recognized_USD` | Recognized contracted revenue; zero for Held | Separates delivered economics from open exposure. Zero Held revenue is not zero commercial value. |
| `Gross_Margin_USD` | Recognized revenue minus total cost | Dollar accounting result. Aggregate dollars first; keep Held separate from delivered margin interpretation. |
| `Gross_Margin_Pct` | Margin ÷ contracted revenue | Unsafe as a raw headline. Rebuild aggregate rates and state the denominator. Emergency-mode values reflect fixed ocean-rate contracts. |
| `DIFOT_Met` | Delivery in full/on time outcome | Delivered service metric. Use 51/51 Direct versus 113/138 post-delivered; exclude Held from delivered denominators. |
| `Cost_per_Ton_USD` | Total cost ÷ tonnes | Rate normalization and validation aid. Recompute aggregate cost ÷ aggregate tonnes. |
| `Revenue_per_Ton_USD` | Contracted revenue ÷ tonnes | Fixed-rate counterpart to cost/ton. Recompute from sums. |
| `Route_Margin_Sensitivity_USD` | Cost/ton premium versus product-specific median Direct cost/ton, multiplied by tonnes | Primary incremental-cost anchor. Validate and use as supplied; do not replace it with a cruder benchmark. |
| `Customer_Concentration_Risk_Pct` | Customer share of raw-dataset contracted revenue | QA only because raw duplicates/source version affect the denominator. Recompute from unique shipments. |
| `War_Risk_Insurance_Burden_Pct` | Insurance ÷ cargo value × 100 | Recorded burden, not a standalone war-risk premium or disruption probability. Recompute aggregate burden from sums. |
| `Delay_Cost_Attribution_Pct` | Penalty ÷ total cost × 100 | Mechanism indicator. Recompute from sums; do not average row percentages. |

## Mandatory hazard rules

### 1. Duplicate-safe aggregation

Every portfolio or segment metric must begin from one canonical row per `Shipment_ID`. Exact duplicates may be collapsed once; conflicting duplicates require source adjudication. Never silently keep the first row.

### 2. Emergency-mode gross margins

Air Bridge and Overland Truck were emergency substitutes priced against fixed ocean-rate contracts. An extreme negative margin does not prove that the mode is intrinsically uneconomic. It proves that the observed premium was not recovered under those contracts. Judge the mode by customer/product criticality, live feasible alternatives, avoided loss, and recoverable surcharge.

### 3. Supplied route sensitivity

`Route_Margin_Sensitivity_USD` already uses a product-specific pre-blockade Direct cost/ton benchmark. Do not recreate an all-product or route-average substitute. Five product benchmarks reproduce from the cleaned file. Refined Petrochemicals imply $7.224/t in the supplied field versus $7.186/t from the cleaned Direct rows, creating a $104,746 all-file reconciliation difference and a maximum $3,572 row difference. Retain the supplied field provisionally and rerun the check on the 246-row source.

### 4. Held shipments

Held rows have zero recognized revenue and no actual transit time by design. They must remain visible as an open-exposure pool. Do not drop them through `dropna`, impute transit, assign delivered DIFOT of 0%, or treat current accounting loss as a completed-shipment unit-economics verdict.

### 5. Concentration

The stored concentration percentage is repeated at row level and reflects the unreconciled raw denominator. Never sum or average it. Recompute account contracted revenue divided by de-duplicated portfolio contracted revenue.

### 6. Ratio aggregation

Do not average row-level margins, cost/ton, revenue/ton, insurance burden, delay attribution, or concentration. Rebuild each rate from aggregate numerators and denominators.

### 7. Correlation and counterfactuals

The file is a descriptive crisis snapshot, not a randomized route experiment. Product mix, route selection, capacity, destination, and timing differ. Observed route comparisons support pilots and guardrails, not causal claims that a different route would have produced the same outcome.

## Five strategic tensions

1. **Stay versus reroute:** holding preserves distance economics only in theory while revenue remains unrecognized and cost accumulates. Rerouting may restore flow but increase cost, transit, and working-capital pressure.
2. **Margin versus customer relationship:** absorbing cost may protect service and trust, but open-ended absorption destroys economics. Passing through cost protects contribution but may create friction under inflexible contracts.
3. **Service versus unit economics:** fast emergency modes may protect DIFOT for critical cargo while producing poor observed economics under legacy pricing. The premium must be justified shipment by shipment.
4. **Revenue scale versus exposure quality:** large accounts drive enterprise dollars, while smaller accounts may have worse rate severity, delay attribution, or route dependence. Dollars size the decision; normalized exposure changes the treatment.
5. **Tactical response versus structural redesign:** clearing the queue or switching routes solves the immediate episode, not the recurring concentration, contract, insurance, and optionality problem.

## Evidence standards

The official case requires the final answer to:

- quantify financial impact wherever possible;
- use rates and unit economics where scale would distort comparison;
- show portfolio and segment/lane views together when they lead to different conclusions;
- state assumptions, exclusions, and data treatments;
- avoid confusing correlation with causation;
- use the pre-crisis Direct benchmark only where defensible;
- validate derived formulas and denominator definitions; and
- attach a clear owner, time horizon, and trigger/metric to every recommendation.

Published case-competition rubrics reinforce the same pattern: identify the pertinent issue, connect qualitative and quantitative evidence, recommend a practical response, show implementation and controls, and defend the logic consistently in Q&A.[^3][^4] There is no public Quantiz’26 scoring rubric for this case; those external criteria are directional preparation evidence, not official Quantiz weights.

## What the final board story must not become

- an exhaustive 29-column tour;
- a “single worst route” ranking;
- an average of unsafe percentages;
- a route heat map without reconciled dollars;
- a claim that Air or Overland is intrinsically bad;
- a second, cruder version of route sensitivity;
- a delivered-route analysis that accidentally removes Held shipments;
- a causal route recommendation from observational differences;
- predictive ML without a labelled outcome; or
- Monte Carlo precision without defensible distributions and dependencies.

## Sources

[^1]: Quantiz’26. `R2-War Room Masterplan Case Study(1).pdf`, pp. 1–6, supplied case document.
[^2]: Quantiz’26. `R2-WAR ROOM MASTERPLAN-cleaned(1).xlsx`, `Shipment_Data` and `Data_Dictionary_Enriched`, supplied workbook.
[^3]: HKU Asia Case Research Centre. [Judging Criteria](https://competition.acrc.hku.hk/About/JudgingCriteria).
[^4]: Institute for Supply Management. [Global Case Competition Requirements](https://utah.ismworld.org/globalassets/pub/awards/22-23-ism-case-competition-requirements.pdf).
