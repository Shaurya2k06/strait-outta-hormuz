import dashboardData from './dashboard-data.json'

const SUPPORTED_SCHEMA_VERSION = '2.0.0'
const requiredKeys = [
  'schemaVersion',
  'metadata',
  'qa',
  'universes',
  'financialBridge',
  'portfolio',
  'routes',
  'customers',
  'products',
  'decisionCells',
  'heldLedger',
  'routeEvidence',
  'decisionRegister',
  'appendixDiagnostics',
  'methodology',
]

if (dashboardData.schemaVersion !== SUPPORTED_SCHEMA_VERSION) {
  throw new Error(`Unsupported dashboard schema: ${dashboardData.schemaVersion ?? 'unknown'}`)
}

const absentKeys = requiredKeys.filter((key) => !(key in dashboardData))
if (absentKeys.length) {
  throw new Error(`Incomplete analytical output: requires ${absentKeys.join(', ')}`)
}

export { SUPPORTED_SCHEMA_VERSION }
export default dashboardData
