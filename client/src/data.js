export const controls = {
  canonicalRows: 243,
  statedRows: 246,
  contractedRevenue: 113313425.66,
  recognizedRevenue: 87389145.83,
  heldRevenue: 25924279.83,
  shockRows: 192,
  deliveredRows: 138,
  heldRows: 54,
  adverseSensitivity: 178709588.63,
  signedSensitivity: 177481147.59,
  deliveredMargin: -157703390.39,
  heldCost: 34315352.1,
  heldPenalty: 26015708.84,
  heldInsurance: 4481012.26,
  heldDays: 1234,
  heldMedianDays: 20.5,
  heldMaxDays: 47,
  directDIFOT: 100,
  postDIFOT: 81.9,
  favourableOffset: 1228441.04,
}

export const routes = [
  { name: 'Direct / benchmark', kind: 'reference', shipments: 51, delivered: 51, difot: 100, costPerTon: 7.26, sensitivity: 0.25, adverse: 0.25, contracted: 17.07, delay: 27, burden: 0.4 },
  { name: 'Cape of Good Hope', kind: 'delivered', shipments: 49, delivered: 49, difot: 67.3, costPerTon: 15.92, sensitivity: 29.98, adverse: 29.98, contracted: 29.19, delay: 94, burden: 1.82 },
  { name: 'Pipeline Bypass', kind: 'delivered', shipments: 24, delivered: 24, difot: 62.5, costPerTon: 34.57, sensitivity: 134.89, adverse: 134.89, contracted: 40.43, delay: 43, burden: 0.88 },
  { name: 'Overland Truck', kind: 'delivered', shipments: 43, delivered: 43, difot: 100, costPerTon: 590.36, sensitivity: 0.06, adverse: 0.11, contracted: 0.43, delay: 14, burden: 0.84 },
  { name: 'Air Bridge', kind: 'delivered', shipments: 22, delivered: 22, difot: 100, costPerTon: 5613.55, sensitivity: 1.08, adverse: 1.08, contracted: 0.27, delay: 0, burden: 0.5 },
  { name: 'Held in Gulf', kind: 'held', shipments: 54, delivered: 0, difot: null, costPerTon: 11.05, sensitivity: 11.46, adverse: 12.64, contracted: 25.92, delay: 1234, burden: 1.96 },
]

export const customers = [
  { name: 'Meridian Energy Partners', fullShare: 58.34, shipments: 24, adverse: 110.09, contracted: 57.08, severity: 192.88, difot: 63.2, held: 11.22, score: 61, flags: ['DOLLAR PRIORITY', 'DIFOT BREACH'] },
  { name: 'Zenith Crude Traders', fullShare: 20.04, shipments: 10, adverse: 29.62, contracted: 22.71, severity: 130.45, difot: 83.3, held: 9.77, score: 70, flags: ['DIFOT BREACH'] },
  { name: 'Pacific Rim Petrochem', fullShare: 8.14, shipments: 12, adverse: 21.86, contracted: 6.83, severity: 320.24, difot: 66.7, held: 1.99, score: 85, flags: ['DIFOT BREACH', 'TOP DECILE IMPACT'] },
  { name: 'Nordholm Refining Group', fullShare: 5.47, shipments: 7, adverse: 7.81, contracted: 3.87, severity: 201.91, difot: 60, held: 2.03, score: 70, flags: ['DIFOT BREACH', 'LOW SAMPLE'] },
  { name: 'Baltic Fuel Alliance', fullShare: 6.5, shipments: 8, adverse: 7.73, contracted: 4.41, severity: 175.06, difot: 80, held: 1.73, score: 80, flags: ['DIFOT BREACH'] },
]

export const products = [
  { name: 'Crude Oil', shipments: 34, adverse: 139.71, contracted: 79.78, severity: 175.11, difot: 68, score: 60, flags: ['DIFOT BREACH', 'DOLLAR PRIORITY'] },
  { name: 'Refined Petrochemicals', shipments: 27, adverse: 37.39, contracted: 15.11, severity: 247.53, difot: 68.4, score: 83, flags: ['DIFOT BREACH', 'PENALTY HEAVY'] },
  { name: 'High-Tech Components', shipments: 24, adverse: 0.72, contracted: 0.27, severity: 264.59, difot: 100, score: 49, flags: ['HIGH SEVERITY'] },
  { name: 'Pharmaceuticals', shipments: 30, adverse: 0.45, contracted: 0.37, severity: 122.72, difot: 100, score: 41, flags: ['HIGH SEVERITY'] },
  { name: 'Industrial Machinery', shipments: 44, adverse: 0.3, contracted: 0.48, severity: 63.09, difot: 73.3, score: 47, flags: ['DIFOT BREACH'] },
  { name: 'Consumer Goods', shipments: 33, adverse: 0.13, contracted: 0.23, severity: 56.05, difot: 87, score: 20, flags: ['LOW SEVERITY'] },
]

export const cells = [
  { customer: 'Meridian Energy Partners', product: 'Crude Oil', route: 'Pipeline Bypass', shipments: 12, adverse: 89.79, contracted: 29.54, severity: 303.99, difot: 58.3, flags: ['DIFOT BREACH'] },
  { customer: 'Zenith Crude Traders', product: 'Crude Oil', route: 'Pipeline Bypass', shipments: 3, adverse: 20.65, contracted: 6.31, severity: 327.56, difot: 66.7, flags: ['DIFOT BREACH'] },
  { customer: 'Pacific Rim Petrochem', product: 'Refined Petrochemicals', route: 'Pipeline Bypass', shipments: 6, adverse: 17.11, contracted: 3.24, severity: 528.02, difot: 66.7, flags: ['DIFOT BREACH'] },
  { customer: 'Meridian Energy Partners', product: 'Crude Oil', route: 'Cape of Good Hope', shipments: 7, adverse: 16.55, contracted: 16.32, severity: 101.4, difot: 71.4, flags: ['DIFOT BREACH'] },
  { customer: 'Zenith Crude Traders', product: 'Crude Oil', route: 'Cape of Good Hope', shipments: 3, adverse: 6.6, contracted: 6.63, severity: 99.5, difot: 100, flags: [] },
  { customer: 'Nordholm Refining Group', product: 'Refined Petrochemicals', route: 'Pipeline Bypass', shipments: 2, adverse: 4.72, contracted: 0.81, severity: 580.21, difot: 50, flags: ['DIFOT BREACH', 'LOW SAMPLE'] },
  { customer: 'Meridian Energy Partners', product: 'Crude Oil', route: 'Held in Gulf', shipments: 5, adverse: 3.75, contracted: 11.22, severity: null, difot: null, flags: ['HELD OPEN EXPOSURE'] },
  { customer: 'Baltic Fuel Alliance', product: 'Refined Petrochemicals', route: 'Held in Gulf', shipments: 3, adverse: 2.82, contracted: 1.73, severity: null, difot: null, flags: ['HELD OPEN EXPOSURE'] },
]

export const heldQueue = [
  { id: 'SGL-1065', customer: 'Meridian Energy Partners', product: 'Crude Oil', days: 46, penaltyPerDay: 89789.64, penalty: 4.13, revenue: 1.85, option: 'Pipeline validation' },
  { id: 'SGL-1093', customer: 'Baltic Fuel Alliance', product: 'Refined Petrochemicals', days: 38, penaltyPerDay: 49617.71, penalty: 1.89, revenue: 0.63, option: 'Cape pilot' },
  { id: 'SGL-1061', customer: 'Deccan Industrial Works', product: 'Industrial Machinery', days: 47, penaltyPerDay: 405.72, penalty: 0.02, revenue: 0.01, option: 'Overland gate' },
  { id: 'SGL-1072', customer: 'Vantage Pharma Logistics', product: 'Pharmaceuticals', days: 44, penaltyPerDay: 475.64, penalty: 0.02, revenue: 0.01, option: 'Air exception' },
  { id: 'SGL-1097', customer: 'Novastar Electronics', product: 'High-Tech Components', days: 37, penaltyPerDay: 573.62, penalty: 0.02, revenue: 0.01, option: 'Air / overland' },
  { id: 'SGL-1083', customer: 'Coral Bay Consumer Brands', product: 'Consumer Goods', days: 41, penaltyPerDay: 135.92, penalty: 0.01, revenue: 0.01, option: 'Cape validation' },
]

export const scoreRows = {
  Customer: [
    { name: 'Pacific Rim Petrochem', score: 85, M: 320.24, I: 1.36, D: 14.5, C: 8.14, sample: 12 },
    { name: 'Baltic Fuel Alliance', score: 80, M: 175.06, I: 1.74, D: 33.95, C: 6.5, sample: 8 },
    { name: 'Nordholm Refining Group', score: 70, M: 201.91, I: 1.58, D: 12.97, C: 5.47, sample: 7 },
    { name: 'Zenith Crude Traders', score: 70, M: 130.45, I: 1.7, D: 16.88, C: 20.04, sample: 10 },
    { name: 'Meridian Energy Partners', score: 61, M: 192.88, I: 1.34, D: 7.76, C: 58.34, sample: 24 },
  ],
  Route: [
    { name: 'Pipeline Bypass', score: 71, M: 333.69, I: 0.88, D: 1.59, C: 46.6, sample: 24 },
    { name: 'Cape of Good Hope', score: 64, M: 102.71, I: 1.82, D: 3.22, C: 38.52, sample: 49 },
    { name: 'Held in Gulf', score: 56, M: 48.77, I: 1.96, D: 75.81, C: 34.02, sample: 54 },
    { name: 'Air Bridge', score: 45, M: 399.31, I: 0.5, D: 0, C: 0.16, sample: 22 },
    { name: 'Overland Truck', score: 14, M: 24.24, I: 0.84, D: 0.89, C: 0.18, sample: 43 },
  ],
  Product: [
    { name: 'Refined Petrochemicals', score: 83, M: 247.53, I: 1.52, D: 18.6, C: 6.98, sample: 27 },
    { name: 'Crude Oil', score: 60, M: 175.11, I: 1.44, D: 9.93, C: 47.44, sample: 34 },
    { name: 'High-Tech Components', score: 49, M: 264.59, I: 0.9, D: 7.81, C: 0.13, sample: 24 },
    { name: 'Industrial Machinery', score: 47, M: 63.09, I: 1.43, D: 22.19, C: 0.26, sample: 44 },
    { name: 'Pharmaceuticals', score: 41, M: 122.72, I: 0.93, D: 12.39, C: 0.19, sample: 30 },
    { name: 'Consumer Goods', score: 20, M: 56.05, I: 1.46, D: 12.22, C: 0.09, sample: 33 },
  ],
}

export const scenarios = [
  { name: 'Normalization', tone: 'mint', detail: 'Disruption days decline; routes, capacity, current quotes and insurance ease.', outputs: 'Contribution • Held revenue • DIFOT • trigger crossings', action: 'Keep controls until release metrics clear.' },
  { name: 'Prolonged disruption', tone: 'amber', detail: 'Current alternatives persist; capacity, delay, fuel and insurance step up.', outputs: 'Same outputs + option utilization + contract recovery', action: 'Extend only dated exceptions that clear the live hurdle.' },
  { name: 'Escalation / next chokepoint', tone: 'red', detail: 'One corridor or insurer is unavailable; Held inflow grows.', outputs: 'Scarce-capacity allocation • unrecognized revenue • service breach', action: 'Exercise options; pause unrecovered commitments.' },
]

export const actions = [
  { priority: '01', type: 'Protect / change / stop', title: 'Release the queue', owner: 'COO', horizon: '0–30 days', trigger: 'Any Held shipment >5 days or Held revenue >5% of portfolio.', release: 'Held revenue <5%; approved routes sustain ≥95% DIFOT for two weekly reviews.' },
  { priority: '02', type: 'Protect / change / stop', title: 'Reopen material account terms', owner: 'CCO', horizon: '0–90 days', trigger: 'Cell sensitivity/revenue >25%, Held revenue >$1m, or contribution-negative cell.', release: 'Sensitivity/revenue <10% and DIFOT ≥95% for 30 days.' },
  { priority: '03', type: 'Protect / change / stop', title: 'Gate the route premium', owner: 'CSCO', horizon: '0–365 days', trigger: 'Recovered surcharge + avoided loss fails to cover current quoted premium.', release: 'Use lower-cost feasible mode once service/economic hurdle clears.' },
  { priority: '04', type: 'Protect / change / stop', title: 'Re-insure by corridor', owner: 'CRO', horizon: '31–90 days', trigger: 'Recorded burden >1.5% of cargo value or top-quartile insurance burden.', release: 'Burden <0.75% for 60 days with better premium + retained loss.' },
  { priority: '05', type: 'Protect / change / stop', title: 'Stop unrecoverable offers', owner: 'CCO', horizon: '31–365 days', trigger: 'Negative contribution persists after route, price, insurance and service redesign.', release: 'Re-enter only with positive prospective contribution and enforceable recovery.' },
]
