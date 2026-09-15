# Strait Outta Hormuz

The dashboard is a generated, provisional war-room snapshot for the supplied
case workbook. `analysis/analyze.py` is the source of truth: it reads
`R2-WAR ROOM MASTERPLAN-cleaned.xlsx`, adjudicates duplicate `Shipment_ID`s,
reconciles the analytical universes, and writes `client/src/dashboard-data.json`
plus `analysis/qa-report.json`.

## Run

```sh
cd client
npm install
npm run verify
npm run dev
```

Use `npm run analyze` after replacing the workbook. It fails on conflicting
duplicates or reconciliation errors. The current file has 243 canonical rows;
the case states 246, so the dashboard remains visibly provisional and does not
prorate or invent the missing records. Use `npm run analyze -- --strict-source`
to make the refresh fail until the case-stated 246 canonical rows are present.

Scenario inputs are owner-editable in the browser and recalculate the displayed
stress outputs; they are proposal defaults until Operations, Procurement,
Commercial and Finance replace them with approved values.

Held shipments stay in a separate open-exposure ledger. Direct is a historical
benchmark. Route comparisons are descriptive and do not establish causality.
