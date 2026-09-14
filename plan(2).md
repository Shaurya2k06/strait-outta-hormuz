# Quantiz’26 “Strait Outta Hormuz” — Exact Analysis Plan

## Outcome and success test

The work will answer one board question: **where is the company exposed, where does that exposure become a business problem, and what should it protect, change, or stop doing?**

The analysis will use one quantitative and narrative spine:

**Hormuz shock → operating vulnerability → commercial transmission → dollars/service at risk → protect/change/stop action with owner and trigger**

The submission succeeds only if it does all of the following:

1. reconciles every portfolio total to one canonical shipment grain;
2. distinguishes expensive operations from economically material, commercially transmitted exposure;
3. shows raw dollars and normalized severity together;
4. keeps open Held exposure separate from completed-shipment economics;
5. turns each material customer × product × route exposure into a specific action;
6. gives every recommendation one accountable owner, horizon, activation trigger, and release/reversal metric; and
7. remains defensible when the original 246-record source and live operating inputs are supplied.

The approach follows real-practice distinctions between shock exposure, vulnerability, and consequence; enterprise totals reconciled to segment actions; and explicit cost-versus-resilience trade-offs.[^3][^4][^5] The Exposure Score follows composite-indicator discipline: transparent construction, normalization, sensitivity testing, and no claim that an ordinal score is a probability.[^6]

## Stage 0 — Freeze the evidence base

### 0.1 Source-version gate

The case states 246 shipment records with intentional duplicate IDs, while the supplied cleaned workbook contains 243 rows, 243 unique `Shipment_ID`s, and no duplicates.[^1][^2] The case also refers to supporting sheets not present in the cleaned workbook.

Until the raw source is reconciled:

- label every calculated number **provisional—243-row cleaned file**;
- do not prorate 243-row results to 246;
- do not infer or manufacture the three missing records;
- do not use the stored concentration percentage as a denominator; and
- block final slide-number freeze, while allowing the method and working recommendations to proceed.

### 0.2 Exact duplicate-adjudication procedure

```text
load every source row without type-coercing identifiers
group rows by Shipment_ID
for each repeated Shipment_ID:
    compare every one of the 29 fields, including blanks
    if all rows are exact duplicates:
        retain one row and log duplicate_count_removed
    else:
        stop aggregation and create a conflict record for source-owner adjudication
assert row_count == count_distinct(Shipment_ID)
assert no null Shipment_ID
write the pre/post row count, exact-duplicate removals, conflicts, and checksum to the QA log
```

No `drop_duplicates(Shipment_ID, keep='first')` shortcut is permitted. Counts, sums, shares, rates, ranks, and charts must all use the resulting canonical table.

### 0.3 Canonical analytical universes

```text
portfolio_unique = one adjudicated row per Shipment_ID
direct_reference = Route_Type == "Direct (Pre-Blockade)"
shock = portfolio_unique excluding direct_reference
post_delivered = shock excluding "Held in Gulf"
held_open = shock where Route_Type == "Held in Gulf"
```

Working counts on the supplied cleaned workbook are 243 portfolio rows, 51 Direct reference rows, 192 shock rows, 138 post-blockade delivered rows, and 54 Held rows. Direct is a historical product benchmark, not a presumed post-blockade option. Held is an open status, not a completed route.

### 0.4 Formula and data-integrity checks

Run these checks before any analysis and again after the raw-file reconciliation:

| Check | Formula / acceptance rule |
| --- | --- |
| Cost identity | `Total_Cost_to_Serve_USD = Freight + Fuel + Insurance + Penalty`; investigate differences above rounding tolerance |
| Margin identity | `Gross_Margin_USD = Revenue_Recognized_USD − Total_Cost_to_Serve_USD` |
| Cost rate | `Cost_per_Ton_USD = Total_Cost_to_Serve_USD / Cargo_Weight_Tons` |
| Revenue rate | `Revenue_per_Ton_USD = Contracted_Freight_Revenue_USD / Cargo_Weight_Tons` |
| Held completeness | `Actual_Transit_Days` blank and `Revenue_Recognized_USD = 0` for Held only |
| Delivered completeness | non-Held rows have actual transit and recognized revenue |
| Concentration | recomputed customer shares sum to 100.0% within rounding tolerance |
| Route sensitivity | reproduce product-specific Direct benchmark; log row and portfolio variance but retain the supplied field provisionally |
| Score | weights sum to 1.00; component denominator is positive; scores lie from 0 to 100 within each universe |
| Roll-up | action-cell dollars reconcile exactly to customer, product, route/status, shock, and portfolio controls |

The cleaned file currently has zero accounting-identity error. Five product sensitivity benchmarks reproduce; Refined Petrochemicals imply $7.224/t in the supplied sensitivity versus $7.186/t from cleaned Direct rows. The resulting all-file difference is $104,746, or 0.059% of the supplied signed exposure, with a maximum $3,572 row difference. Use the supplied `Route_Margin_Sensitivity_USD`; do not replace it with a cruder benchmark.

## Stage 1 — Relevance cut across all 29 fields

A field earns final-deck space only if it locates actionable exposure, explains commercial transmission, or changes an action. Supporting fields may remain in calculations without becoming board headlines.

| # | Column | Treatment | Why it is in or out |
| ---: | --- | --- | --- |
| 1 | `Shipment_ID` | Appendix/QA | Canonical grain and duplicate control; not a board segment. |
| 2 | `Departure_Date` | Supporting | Observation window, cohort and Held-aging control; no seasonality inference from 77 days. |
| 3 | `Route_Type` | Headline | Operating state and route/action lever; Direct benchmark and Held status require separate treatment. |
| 4 | `Product_Category` | Headline | Required for benchmark validity, cargo criticality, and product-route action. |
| 5 | `Cargo_Type` | Supporting | Physical-feasibility guardrail; not a separate headline because it is determined by product in this file. |
| 6 | `Customer_Name` | Headline | Commercial owner and protect/renegotiate/exit grain. |
| 7 | `Customer_Region` | Exclude | Customer home region, not origin, destination, lane, node, or jurisdiction; adds no customer-rank or action information. Reopen only if management supplies a relevant criterion. |
| 8 | `Customer_Since` | Appendix/QA | Tenure is not lifetime value, renewal probability, strategic tier, or switching cost. |
| 9 | `Cargo_Weight_Tons` | Supporting | Denominator for aggregate per-ton economics and sensitivity validation. |
| 10 | `Cargo_Value_USD` | Supporting | Denominator for insurance burden and goods-at-risk context; not company revenue. |
| 11 | `Contracted_Freight_Revenue_USD` | Headline | Fixed customer price, concentration denominator, and Held commercial value. |
| 12 | `Planned_Transit_Days` | Supporting | Route-specific service baseline. |
| 13 | `Actual_Transit_Days` | Supporting | Delivered service duration; never imputed for Held. |
| 14 | `Delay_Days` | Headline | Operational-to-commercial bridge; means completed delay for delivered and days stuck for Held, so split the uses. |
| 15 | `Freight_Cost_USD` | Supporting | Cost-waterfall component already included in total cost. |
| 16 | `Fuel_Cost_USD` | Supporting | Driver/scenario component already included in total cost. |
| 17 | `Insurance_Cost_USD` | Headline | Dollar input for re-insure action; pair with insurance/cargo-value burden. |
| 18 | `Penalty_Cost_USD` | Headline | Monetized service failure; pair with DIFOT and recognize omitted relationship/working-capital losses. |
| 19 | `Total_Cost_to_Serve_USD` | Headline | Authoritative current cost and financial-bridge control. |
| 20 | `Revenue_Recognized_USD` | Headline | Separates delivered earnings from contracted-but-unrecognized Held value. |
| 21 | `Gross_Margin_USD` | Headline | Commercial consequence in dollars; aggregate first and split Held from delivered. |
| 22 | `Gross_Margin_Pct` | Appendix/QA | Quarantined source ratio. Never average, rank, score, or headline it; rebuild any needed rate from aggregate dollars with a named denominator. |
| 23 | `DIFOT_Met` | Headline | Core service outcome. Compare regimes using delivered denominators; Held remains open exposure. |
| 24 | `Cost_per_Ton_USD` | Supporting | Rate-normalized economics; rebuild as aggregate cost ÷ aggregate tonnes. |
| 25 | `Revenue_per_Ton_USD` | Supporting | Fixed contract-rate counterpart; rebuild from aggregate sums. |
| 26 | `Route_Margin_Sensitivity_USD` | Headline | Case-provided product-benchmarked incremental-cost anchor; validate and use, preserving signed and positive-only views. |
| 27 | `Customer_Concentration_Risk_Pct` | Appendix/QA | Repeated raw-denominator field; use only to document the mismatch. Recompute concentration from canonical contracted revenue. |
| 28 | `War_Risk_Insurance_Burden_Pct` | Supporting | Score/re-insurance component; recompute as aggregate insurance ÷ aggregate cargo value. |
| 29 | `Delay_Cost_Attribution_Pct` | Supporting | Score/service mechanism; recompute as aggregate penalty ÷ aggregate total cost. |

This cut deliberately excludes an exhaustive route atlas, customer-region story, tenure-based relationship valuation, and raw percentage rankings. None changes the decision with the current evidence.

## Stage 2 — Build the decision dataset

### 2.1 Master action table

Create one row per **observed or Operations-validated feasible customer × product × route/status cell**. On the cleaned file there are 44 observed shock cells. Add a low-sample warning for fewer than three shipments and a singleton warning for one shipment.

Each row contains:

- unique shipment count and tonnes;
- contracted and recognized revenue;
- total cost and gross-margin dollars;
- supplied signed sensitivity and positive-only adverse sensitivity;
- adverse sensitivity ÷ contracted revenue for delivered cells;
- insurance dollars and aggregate insurance burden;
- penalty dollars and aggregate delay-cost attribution;
- delivered DIFOT and actual/planned transit for delivered cells;
- days stuck and contracted-but-unrecognized revenue for Held cells;
- recomputed customer concentration;
- Exposure Score components, rank, hard flags, action, owner, horizon, trigger, and release rule.

All customer, product, route/status, and portfolio views are roll-ups of this table. No independent worksheet may use a different denominator.

### 2.2 Feasibility guardrail

Use observed cargo-format combinations only until Operations validates additional options:

- Pipeline Bypass is observed only for bulk liquid;
- Air Bridge and Overland Truck are observed only for containers; and
- Cape is observed for both.

Absence is neither evidence of feasibility nor proof of infeasibility. Mark an unobserved combination **not assessed—Operations validation required**. Route comparisons must be product/cargo matched; the board should not compare bulk Pipeline economics with a container Air outcome as if the shipments were interchangeable.

## Stage 3 — Quantify operational exposure

The operating analysis asks whether the network moved cargo, at what service degradation, and where open exposure accumulated. It does not declare the most expensive route the worst business problem.

### Delivered metrics

For Direct reference and each post-blockade delivered route/product cell, calculate:

```text
DIFOT = count(DIFOT_Met == "Y") / delivered shipment count
transit index = sum(Actual_Transit_Days) / sum(Planned_Transit_Days)
positive delay per shipment = sum(max(Delay_Days, 0)) / delivered shipment count
penalty rate = sum(Penalty_Cost_USD) / sum(Revenue_Recognized_USD)
cost per ton = sum(Total_Cost_to_Serve_USD) / sum(Cargo_Weight_Tons)
```

The working regime headline is Direct 51/51 = 100.0% DIFOT versus post-blockade delivered 113/138 = 81.9%. Cape and Pipeline are the scalable observed delivered alternatives, but route selection, cargo mix, capacity, and destination are confounded. Their performance supports a controlled product-matched pilot, not a causal rerouting claim.

For bulk-only comparability, carry the working reference: Cape sensitivity/revenue 102.9%, DIFOT 75.0%, and $15.79/t versus Pipeline 333.7%, 62.5%, and $34.57/t; Cape insurance burden is higher at 1.82% versus 0.88%. Refresh with the reconciled source and live capacity/quote data before dispatch.

### Held metrics

Do not calculate delivered transit, delivered DIFOT, or realized margin percentage for Held. Report:

```text
held shipment count
contracted but unrecognized revenue
cost accrued to date
insurance and penalties
total, median, p90 and maximum days stuck
held revenue and shipment count by customer/product
daily penalty run rate where source timing supports it
```

Working controls are 54 Held shipments, $25.924m contracted but unrecognized revenue, $34.315m cost to date, $26.016m penalties, $4.481m insurance, and 1,234 cumulative days stuck. The queue is prioritized by penalty per day and revenue unlock, subject to cargo integrity and physical feasibility.

## Stage 4 — Quantify commercial transmission

### 4.1 Customer concentration

Recompute—not sum or average—the share:

```text
customer concentration =
    sum(customer Contracted_Freight_Revenue_USD on canonical rows)
    / sum(portfolio Contracted_Freight_Revenue_USD on canonical rows)
```

The working denominator is $113,313,425.66. Report both account dollars and share. Do not infer bargaining power or lifetime value from the share alone.

### 4.2 Incremental-cost exposure

For every delivered action segment `S`:

```text
signed sensitivity_S = sum(Route_Margin_Sensitivity_USD)
positive adverse sensitivity_S = sum(max(Route_Margin_Sensitivity_USD, 0))
favourable offset_S = sum(min(Route_Margin_Sensitivity_USD, 0))
severity_S = positive adverse sensitivity_S / sum(Contracted_Freight_Revenue_USD)
```

Use positive-only dollars for Pareto and prioritization so favourable rows do not conceal adverse exposure. Show signed sensitivity as a reconciliation column. Held remains an open-exposure flag and does not receive a delivered-severity rate in the action table.

Working shock controls are $177.481m signed and $178.710m positive-only adverse sensitivity, with $1.228m favourable offsets. Dollar Pareto findings to refresh are:

- Meridian + Zenith + Pacific: 90.4% of positive shock sensitivity;
- Pipeline + Cape: 92.3%;
- Crude + Refined: 99.1%; and
- Meridian + Zenith: 81.0% of Held contracted revenue.

Mark cumulative 50%, 70%, and 80% Pareto breakpoints. The relevance rule is not “top five”; it is the smallest set that captures a board-material dollar pool while retaining high-rate overrides.

### 4.3 Contribution-margin bridge

Do not add sensitivity, insurance, and penalties as if they were independent losses. Insurance and penalty are already inside current total cost and help explain the mechanism.

For delivered rows:

```text
benchmark Direct-equivalent cost = actual total cost − supplied signed sensitivity
benchmark contribution = recognized revenue − benchmark Direct-equivalent cost
observed contribution = benchmark contribution − supplied signed sensitivity
```

Then display freight, fuel, insurance, and penalty as a decomposition of observed cost, not additional impacts. Put Held in a separate panel: contracted revenue awaiting recognition, cost accrued, penalties, insurance, and days stuck.

## Stage 5 — Exposure Score and hard flags

### 5.1 Formula

Use the composite only to prioritize vulnerability and treatment **within** a universe:

$$
\text{Exposure Score}=0.45M+0.15I+0.20D+0.20C
$$

| Component | Definition after aggregation | Weight | Rationale |
| --- | --- | ---: | --- |
| `M` | positive adverse sensitivity ÷ contracted revenue on the 192 shock rows | 45% | Fixed revenue meeting changed cost is the central commercial mechanism. |
| `I` | insurance cost ÷ cargo value on the 192 shock rows | 15% | Captures insurability burden, but is capped because insurance is already embedded in cost/sensitivity. |
| `D` | penalty cost ÷ total cost-to-serve on the 192 shock rows | 20% | Captures monetized service failure and changes the service response. |
| `C` | customer share of full unique-portfolio contracted revenue | 20% | Captures structural dependence. Route/product/action-cell `C` is the contracted-revenue-weighted underlying customer share. |

For customer, route/status, and product universes separately:

1. aggregate raw numerators and denominators first;
2. cap each raw component at that universe’s 5th and 95th percentiles;
3. map the capped values to minimum-rank empirical percentiles from 0 to 100;
4. apply the weights and display a whole-number score; and
5. show raw dollars, raw rates, universe name, rank, and sample size beside the score.

The score is an ordinal priority index—not expected loss, a disruption probability, a causal coefficient, or a value-at-risk estimate. Customer, route, and product scores cannot be compared with one another.

### 5.2 Working score controls

| Universe | Working ranking |
| --- | --- |
| Customer | Pacific 85; Baltic 80; Nordholm 70; Zenith 70; Meridian 61 |
| Route/status | Pipeline 71; Cape 64; Held 56; Air 45; Overland 14 |
| Product | Refined Petrochemicals 83; Crude Oil 60; High-Tech 49; Industrial Machinery 47; Pharmaceuticals 41; Consumer Goods 20 |

Meridian remains the first dollar-protection priority even though it ranks fifth on normalized customer vulnerability. Raw dollars decide board materiality; the score diagnoses the mechanism and sequences treatment within the material set.

### 5.3 Overlap and robustness tests

- Calculate Spearman correlations between component values and disclose any `|rho| ≥ 0.70`.
- In the cleaned data, route-level `I` and `D` have `rho = 1.000`. Treat them as one 35% operational-friction pillar for interpretation, then retest `I = 5%`, `D = 30%`. Current scores, ranks, and actions do not change.
- Run eight one-at-a-time weight tests, moving one component ±10 percentage points and renormalizing the other weights proportionally.
- Report whether the customer top four, route top two, product top two, hard flags, and actions change—not merely the correlation of score values.
- If winsorization changes no ranks, say so; do not imply it solved an outlier problem.

### 5.4 Non-compensatory flags

A favourable average score must not hide a hard failure. Carry these flags separately:

- `HELD_OPEN_EXPOSURE` for every Held cell;
- `TOP_DECILE_IMPACT` for top-decile positive adverse dollars within the relevant universe;
- `DELIVERED_NEGATIVE_MARGIN` only for delivered cells with negative aggregate contribution;
- `DIFOT_BREACH` for delivered DIFOT below 90%; and
- `LOW_SAMPLE` for fewer than three shipments.

Held-only cells never receive a delivered-margin or delivered-DIFOT flag.

## Stage 6 — Resolve the five strategic tensions

| Tension | Evidence-backed position | What changes |
| --- | --- | --- |
| Stay vs. reroute | End hold-by-default; use cargo-specific hierarchy and a product-matched Cape pilot. | Clear the Held queue while requiring feasibility, live quote, and service-window checks. |
| Margin vs. relationship | Protect the relationship, not the legacy price. | Give material accounts a dated bridge while reopening war-risk, fuel, route-premium, and service terms. |
| Service vs. unit economics | Use Overland first for feasible containers; Air only by approved, quantified exception. | Require recovered surcharge plus avoided loss to cover the current prospective incremental quote. |
| Revenue scale vs. exposure quality | Dollars set board priority; the score sets treatment; flags override the average. | Resource Meridian/Zenith/Pacific first in dollars, with Pacific/Baltic/Nordholm severity shaping pricing intensity. |
| Tactical vs. structural | Structural redesign is mandatory; emergency exceptions expire within 90 days. | Add corridor options, contract reopeners, route-specific insurance, and quarterly stress tests. |

These are positions, not “it depends” branches. Missing evidence changes the execution gate, not the strategic direction.

## Stage 7 — Scenario and sensitivity tree

Use three transparent decision scenarios, not unsupported probabilities:

| Scenario | Variables to change | Outputs to recompute | Decision use |
| --- | --- | --- | --- |
| Normalization | disruption days decline; routes/capacity recover; current quotes and insurance ease | contribution, Held revenue, DIFOT, trigger crossings | Keep controls until release metrics clear; do not release based on the scenario label. |
| Prolonged disruption | current alternatives persist; capacity, delay, fuel, and insurance step up | same outputs plus option utilization and contract recovery | Extend only dated exceptions that clear the live hurdle; activate repricing and insurance actions. |
| Escalation / next chokepoint | one alternative corridor/insurer unavailable; Held inflow grows | scarce-capacity allocation, unrecognized revenue, service breach, trigger crossings | Exercise options, allocate by criticality and avoided loss, pause unrecovered commitments. |

Required assumptions are disruption duration, route availability/capacity, current freight and fuel quotations, insurance burden, delay/DIFOT, and contract recovery. Operations/Network Planning owns feasibility, capacity, ETA, and live quote; Commercial owns recoverable surcharge and quantified customer/stockout loss; Finance validates contribution; Legal validates enforceability.

Use a one-way tornado only when a changed assumption moves an action or crosses a trigger. Use Monte Carlo only after defensible distributions and dependencies are available; otherwise it would create false precision. Scenario stress testing is a decision discipline, while the score weight tests address ranking robustness—do not conflate them. Supply-chain resilience stress testing is consistent with established practice, but the scenario inputs here must remain case- or owner-sourced.[^7]

## Stage 8 — Board exhibits that survive the relevance cut

| # | Exhibit | Exact content | Why it deserves space |
| ---: | --- | --- | --- |
| 1 | Executive exposure bridge | contracted revenue → recognized revenue and Held backlog; benchmark contribution → signed sensitivity → observed margin; service regime beneath | Establishes the one financial/service through-line without double counting. |
| 2 | Operational exposure table | Direct reference, Cape, Pipeline, Overland, Air, Held; counts, tonnes, DIFOT or n.a., actual/planned, delay/aging, cost/t, insurance burden | Separates delivery degradation, emergency service protection, and open exposure. |
| 3 | Customer Pareto | positive adverse dollars by customer, cumulative share, full-portfolio concentration, severity, Held revenue | Identifies the minimum material account set and prevents a high-rate/small-dollar distraction. Pareto is a prioritization aid, not a universal 80/20 law.[^8] |
| 4 | Value-versus-vulnerability bubble | x = exposure severity or score; y = positive sensitivity dollars; bubble = contracted revenue; flag symbols for Held/service failure | Reconciles scale with exposure quality and identifies different treatments. |
| 5 | Score decomposition | leading customer, route/status, and product rows with raw M/I/D/C, score, rank, dollars, sample warning, hard flag | Makes the score auditable and prevents a black-box league table. |
| 6 | Held release ledger | shipment/account/product, days stuck, penalty/day, revenue unlock, accumulated cost, feasible release option, owner | Converts Held from an excluded null-transit group into a 0–30-day operating queue. |
| 7 | Three-scenario decision table | scenario assumptions, financial/service outputs, trigger crossings, action change; one tornado only if useful | Tests the next-disruption response without invented probability precision. |
| 8 | Five-lever action table | protect/change/stop, accountable owner, horizon, activation trigger, release/reversal metric, missing input owner | Makes the recommendation executable and Q&A-ready. |

Appendix only: 29-field relevance map, duplicate/conflict log, formula validation, sensitivity reproduction, score method and all weight tests, 44-cell master action table, all route/product cuts, and source reconciliation.

## Stage 9 — Recommendation register

The following is the working action template. Thresholds are board risk-appetite proposals, not statistical facts.

| Priority | Protect / change / stop | Accountable owner | Horizon | Activation trigger | Release / reversal metric |
| ---: | --- | --- | --- | --- | --- |
| 1 | **Protect** customer-critical cargo; **change** to a release queue and cargo-specific route hierarchy; **stop** open-ended holding and unpriced dispatch. | COO | 0–30 days | any shipment Held >5 calendar days or Held revenue >5% of portfolio revenue | Held revenue <5% and approved release routes sustain ≥95% DIFOT for two weekly reviews |
| 2 | **Protect** continuity for Meridian/Zenith/Pacific first by dollars and Baltic/Nordholm in the score-led second wave; **change** war-risk/fuel/route terms and service windows; **stop** new unrecovered commitments when sharing is rejected. | CCO | 0–30 days for material accounts; 31–90 days second wave | customer or cell sensitivity/revenue >25%, Held revenue >$1m, or contribution-negative cell | sensitivity/revenue <10% and DIFOT ≥95% for 30 days; otherwise dated executive exception |
| 3 | **Protect** feasible bulk/container alternatives; **change** to product-matched Cape/Pipeline pilot and Overland-first container gate; **stop** Air at legacy ocean rates or approval from DIFOT alone. | Chief Supply Chain Officer | 0–30-day pilot; 90–365-day options | premium move fails `recovered surcharge + quantified avoided loss ≥ current quoted incremental cost`; or corridor exceeds structural trigger | use lower-cost feasible mode when it meets the service window; options lapse only after two quarterly stress tests clear |
| 4 | **Protect** insurable continuity; **change** to pooled/route-specific cover evaluated on premium plus retained loss; **stop** emergency renewal from headline premium alone. | CRO | 31–90 days | recorded burden >1.5% of cargo value or insurance component enters its universe’s top quartile | burden <0.75% for 60 days and alternative remains better on premium plus retained loss |
| 5 | **Protect** only strategically justified, recoverable service offers; **change** contribution-negative cells after mitigation; **stop/exit** repeated unrecoverable Air or customer × product × route offers. | CCO | 31–90 days; structural exit 90–365 days | delivered cell remains negative after route, price, insurance, and service redesign, or hard flag persists through two reviews | re-enter only with positive prospective contribution, enforceable recovery clause, and no open Held/service flag |

### Common board-materiality rule

Escalate a segment when it represents at least 5% of portfolio contracted revenue or positive sensitivity, its positive sensitivity exceeds 100% of its own revenue, or any applicable non-compensatory flag is active. Release only after two consecutive monthly reviews show positive contribution, the segment leaves its universe’s score top quartile, and every applicable hard flag clears.

### Structural-capacity rule

Procure route options when a stress test shows one corridor carrying more than 50% of critical disrupted volume or more than 10% of portfolio revenue becoming unrecognized. Let an option lapse only after two consecutive quarterly tests show neither breach and the feasible network meets the approved service/economic hurdle.

## Stage 10 — Deliberate exclusions

Exclude the following unless new evidence makes one action-relevant:

- no single “worst route” conclusion;
- no exhaustive chart dump, SWOT, PESTLE, Five Forces, or decorative map;
- no average of row-level margin, concentration, cost/t, insurance, or delay percentages;
- no intrinsic condemnation of Air or Overland from emergency-mode gross margin;
- no cruder reconstruction of route sensitivity;
- no imputed Held transit, delivered DIFOT, or realized margin rate;
- no causal route-performance claim from observational data;
- no regression framed as causal decomposition;
- no predictive ML without a labelled outcome;
- no Monte Carlo without defensible distributions and correlations;
- no invented customer lifetime value, stockout loss, route capacity, contract flexibility, current rate, or switching probability; and
- no chart or metric that fails the materiality + commercial transmission + actionability test.

## Stage 11 — QA and Q&A proof pack

Before presentation, require signed checks from the analysis owner:

1. source reconciliation completed or every number visibly marked provisional;
2. canonical unique-shipment assertion passes;
3. customer shares use the canonical $113.313m working denominator or refreshed equivalent;
4. all ratios are rebuilt from aggregate numerators and denominators;
5. Direct, post-delivered, and Held universes are never silently blended;
6. the supplied sensitivity validation and Refined variance are disclosed;
7. raw dollars appear beside every score and scores stay within-universe;
8. the route I–D overlap and all weight-test action stability are disclosed;
9. physical feasibility precedes economic route ranking;
10. every action row has one owner, one horizon, an activation trigger, and a release/reversal metric;
11. every board exhibit reconciles to the master action table; and
12. the team can answer “why is this a business problem rather than merely a high cost?” for every headline.

The Q&A appendix should also show the rejected alternatives and why: blended Held transit, row-average margins, raw concentration, all-product route benchmarks, intrinsic Air/Overland judgments, and unsupported predictive precision. Published competition rubrics consistently reward issue relevance, integrated qualitative/quantitative reasoning, practicality, implementation, and defensible answers; this proof pack is designed around those tests.[^9][^10]

## Sources

[^1]: Quantiz’26. `R2-War Room Masterplan Case Study(1).pdf`, pp. 1–6, supplied case document.
[^2]: Quantiz’26. `R2-WAR ROOM MASTERPLAN-cleaned(1).xlsx`, `Shipment_Data` and `Data_Dictionary_Enriched`, supplied workbook.
[^3]: McKinsey Global Institute. [Risk, resilience, and rebalancing in global value chains](https://www.mckinsey.com/~/media/mckinsey/business%20functions/operations/our%20insights/risk%20resilience%20and%20rebalancing%20in%20global%20value%20chains/risk-resilience-and-rebalancing-in-global-value-chains-full-report-vh.pdf).
[^4]: Boston Consulting Group. [Designing resilience into global supply chains](https://www.bcg.com/publications/2020/resilience-in-global-supply-chains).
[^5]: Kearney. [Resilient supply chains](https://www.kearney.com/service/operations-performance/resilient-supply-chains).
[^6]: OECD/JRC. [Handbook on constructing composite indicators: methodology and user guide](https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf).
[^7]: MIT Center for Transportation & Logistics and Accenture. [Supply-chain resilience stress test](https://newsroom.accenture.com/news/2020/accenture-and-mit-team-to-create-a-supply-chain-resilience-stress-test).
[^8]: American Society for Quality. [Pareto chart](https://asq.org/quality-resources/pareto).
[^9]: HKU Asia Case Research Centre. [Judging Criteria](https://competition.acrc.hku.hk/About/JudgingCriteria).
[^10]: Institute for Supply Management. [Global Case Competition Requirements](https://utah.ismworld.org/globalassets/pub/awards/22-23-ism-case-competition-requirements.pdf).
