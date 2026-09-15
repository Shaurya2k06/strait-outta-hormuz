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
duplicates or reconciliation errors. The approved source in this checkout is
`R2-WAR ROOM MASTERPLAN-cleaned.xlsx`: 243 raw rows → 243 canonical rows,
with its SHA-256 hash and duplicate-adjudication artifact registered. The
dashboard still withholds scenario outputs until owner-approved forward route
inputs are present. Use `npm run analyze -- --strict-source` to verify the
source contract and `npm run verify:board` before a board release.
Use `npm run verify:board` before any board release; it additionally requires
the approved owner-supplied forward ledger inputs.

Scenario output is generated only from approved forward inputs. Until those
inputs are supplied, the UI shows the gate and required fields instead of
calculating proposal economics.

Held shipments stay in a separate open-exposure ledger. Direct is a historical
benchmark. Route comparisons are descriptive and do not establish causality.
