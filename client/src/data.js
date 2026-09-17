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
  throw new Error(`Unsupported dashboard schema: ${dashboardData.schemaVersion ?? 'missing'}`)
}

const missingKeys = requiredKeys.filter((key) => !(key in dashboardData))
if (missingKeys.length) {
  throw new Error(`Incomplete analytical output: missing ${missingKeys.join(', ')}`)
}

export { SUPPORTED_SCHEMA_VERSION }
export default dashboardData
