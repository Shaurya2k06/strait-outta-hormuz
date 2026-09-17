# Strait Outta Hormuz

This repository contains a dataset-only analytical engine and React evidence
view for the supplied 243-row `Shipment_Data` workbook.

## Analytical contract

- The workbook is the complete source: 243 nonblank, unique `Shipment_ID` values and all required columns must validate before calculation.
- Records stay in three named universes: 51 Direct reference shipments, 138 post-blockade delivered shipments and 54 Held shipments.
- Python is the analytical source of truth. React only formats, filters and presents the generated schema.
- Execution values are owner-entered; the engine does not derive a forward forecast, route-capacity model, clearance model, recovery assumption or unapproved freight/insurance/service input.
- Direct is a historical product-matched benchmark. Route comparisons are observational pilot evidence, never causal, optimal, capacity-feasible or rollout-approved.
- Held shipments are a triage ledger. They are excluded from delivered DIFOT and have no release schedule.
- Total cost already includes freight, fuel, insurance and penalty; those components are disclosed but never added twice.

Generated output uses schema `2.0.0` and contains the financial bridge, exposure ledgers, product-matched route evidence, 44 decision cells, Held ledger, decision register, methodology labels and an appendix-only composite diagnostic.

## Run

```sh
cd client
npm install
npm run verify
npm run dev
```

Refresh the generated JSON after replacing the workbook:

```sh
python3 analysis/analyze.py
python3 analysis/test_analysis.py
```

`analysis/analyze.py` fails with the exact source checks when the 243-row
contract, required columns, row arithmetic, universe reconciliations or output
contract do not pass. `analysis/qa-report.json` is terminal QA output; business
calculations do not depend on it.

## Evidence labels

- `FACT`: directly observed in the accepted workbook.
- `DERIVED`: calculated from accepted workbook fields using documented formulas.
- `PROPOSAL`: a management posture, owner or release condition.
- `INPUT_REQUIRED`: an owner-approved value required for prospective execution.

Before execution, owners must approve the named quote, route-week capacity,
product/cargo feasibility, insurance terms, service requirement, customer
recovery term, effective date and approving owner gates.
