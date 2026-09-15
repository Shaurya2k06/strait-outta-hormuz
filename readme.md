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
duplicates or reconciliation errors. The current checkout contains only the
243-row cleaned derivative, so its source gate is intentionally unverified.
The dashboard withholds scenario outputs until both the approved raw source
contract and owner-approved forward route inputs are present. Use `npm run
analyze -- --strict-source` in the release check; it must fail until the
246-row raw workbook, approved hash, and duplicate adjudication are supplied.
Use `npm run verify:board` before any board release; it additionally requires
the approved owner-supplied forward ledger inputs.

Scenario output is generated only from approved forward inputs. Until those
inputs are supplied, the UI shows the gate and required fields instead of
calculating proposal economics.

Held shipments stay in a separate open-exposure ledger. Direct is a historical
benchmark. Route comparisons are descriptive and do not establish causality.
