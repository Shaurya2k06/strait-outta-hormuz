# Dashboard client

The client imports only `src/dashboard-data.json`, generated from the workbook
by `../analysis/analyze.py`.

```sh
npm run analyze
npm run verify
npm run dev
```

`npm run verify` runs analysis/QA, ESLint, and the production build.
