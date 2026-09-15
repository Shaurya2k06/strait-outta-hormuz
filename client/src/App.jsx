import { lazy, Suspense, useMemo, useState } from 'react'
import {
  actions,
  cells,
  concentration,
  controls,
  customers,
  frontier,
  heldQueue,
  metadata,
  routes,
  scenarios,
  scoreRobustness,
  scoreRows,
} from './data'
import './App.css'

const Charts = lazy(() => import('./Charts.jsx'))
const money = (value, digits = 1) => (value == null ? 'n.a.' : `$${(Number(value) / 1000000).toFixed(digits)}M`)
const percent = (value, digits = 1) => (value == null ? 'n.a.' : `${Number(value).toFixed(digits)}%`)
const perTon = (value) => (value == null ? 'n.a.' : `$${Number(value).toFixed(2)}`)
const dateLabel = (value) => new Date(`${value}T00:00:00Z`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
const routeDifot = (route) => route.difot == null ? <span className="na">open</span> : <span className="cell-pair"><b>{percent(route.difot)}</b><small>{route.difotHits}/{route.deliveredShipments} · {percent(route.difotInterval?.lower)}–{percent(route.difotInterval?.upper)}</small></span>

function calculateScenario(inputs) {
  const clearRate = Math.min(1, Math.max(0, Number(inputs.clearRate) || 0))
  const inflowMultiplier = Math.max(0, Number(inputs.heldInflowMultiplier) || 0)
  const beginningHeldRevenue = controls.heldRevenue
  const inflowRevenue = beginningHeldRevenue * inflowMultiplier
  const beginningHeldTonnes = controls.heldTonnes
  const inflowTonnes = beginningHeldTonnes * inflowMultiplier
  const clearedRevenue = (beginningHeldRevenue + inflowRevenue) * clearRate
  const clearedTonnes = (beginningHeldTonnes + inflowTonnes) * clearRate
  const endingHeldRevenue = beginningHeldRevenue + inflowRevenue - clearedRevenue
  const endingHeldTonnes = beginningHeldTonnes + inflowTonnes - clearedTonnes
  const triggerCrossings = []
  if (endingHeldRevenue > beginningHeldRevenue * 0.05) triggerCrossings.push('Ending Held revenue remains open')
  if (endingHeldTonnes > 0) triggerCrossings.push('Backlog remains after constrained allocation')
  return {
    beginningHeldRevenue,
    inflowRevenue,
    clearedRevenue,
    endingHeldRevenue,
    beginningHeldTonnes,
    inflowTonnes,
    clearedTonnes,
    endingHeldTonnes,
    flowBalanced: Math.abs(beginningHeldTonnes + inflowTonnes - clearedTonnes - endingHeldTonnes) < 0.01,
    triggerCrossings,
    decisionReady: false,
  }
}

function Icon({ name, size = 18 }) {
  const paths = {
    arrow: <path d="M5 12h13m-6-6 6 6-6 6" />,
    chart: <path d="M4 19V5m0 14h16M8 15v-3m4 3V8m4 7V5" />,
    compass: <path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6L12 3Z" />,
    database: <path d="M5 6c0-1.7 3.1-3 7-3s7 1.3 7 3-3.1 3-7 3-7-1.3-7-3Zm0 0v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6m-14 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />,
    flag: <path d="M5 21V4m0 0c4-3 7 3 13 0v9c-6 3-9-3-13 0" />,
    layers: <path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5" />,
    lock: <path d="M6 10h12v10H6zM8 10V7a4 4 0 0 1 8 0v3" />,
    pulse: <path d="M3 12h4l2-7 4 14 2-7h6" />,
    shield: <path d="m12 3 7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3Z" />,
    target: <path d="M12 3a9 9 0 1 0 9 9M12 7a5 5 0 1 0 5 5M12 11a1 1 0 1 0 1 1" />,
    trend: <path d="M4 17 9 12l3 3 7-8M14 7h5v5" />,
    truck: <path d="M3 6h11v10H3zM14 10h4l3 3v3h-7m-8 4a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm11 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" />,
  }

  return (
    <svg aria-hidden="true" className="icon" fill="none" height={size} viewBox="0 0 24 24" width={size}>
      {paths[name]}
    </svg>
  )
}

function SectionHeader({ eyebrow, title, copy, action }) {
  return (
    <div className="section-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h2>{title}</h2>
        {copy && <p>{copy}</p>}
      </div>
      {action}
    </div>
  )
}

function MetricCard({ label, value, meta, tone = 'blue', icon }) {
  return (
    <article className={`metric-card tone-${tone}`}>
      <div className="metric-topline"><span>{label}</span><span className="metric-icon"><Icon name={icon} size={16} /></span></div>
      <strong>{value}</strong>
      <small>{meta}</small>
    </article>
  )
}

function RouteTable({ mode, setMode }) {
  const rows = routes.filter((route) => mode === 'all' || (mode === 'delivered' ? route.kind === 'delivered' : route.kind === 'held'))

  return (
    <article className="panel route-panel">
      <div className="panel-heading compact-heading"><div><div className="eyebrow">operating state</div><h3>Delivered routes and one open queue.</h3></div><div className="segmented" role="group" aria-label="Route state filter">{['all', 'delivered', 'held'].map((item) => <button className={mode === item ? 'active' : ''} key={item} onClick={() => setMode(item)} type="button">{item}</button>)}</div></div>
      <div className="table-wrap"><table className="route-table"><thead><tr><th>state</th><th>shipments</th><th>DIFOT / 90% interval</th><th>cost / t</th><th>commercial exposure</th><th>cost accrued</th><th>delay / age</th></tr></thead><tbody>{rows.map((route) => <tr className={`row-${route.kind}`} key={route.name}><td><span className="state-name"><i />{route.name}</span></td><td>{route.shipments}</td><td>{routeDifot(route)}</td><td>{perTon(route.costPerTon)}</td><td className="money-cell">{route.kind === 'reference' ? <span className="na">benchmark</span> : route.kind === 'held' ? money(route.heldRevenue) : money(route.adverse)}</td><td className="money-cell">{money(route.cost)}</td><td>{route.kind === 'held' ? `${route.heldAgeDays.toLocaleString()}d age` : `${route.delayPerShipment.toFixed(2)}d / shipment`}</td></tr>)}</tbody></table></div>
      <div className="panel-footnote"><span className="dot dot-amber" /> Direct is a separate historical benchmark; Held shows open revenue, cost and age rather than delivered route economics.</div>
    </article>
  )
}

function CustomerPareto({ activeCustomer, setActiveCustomer }) {
  const total = controls.adverseSensitivity
  const chartData = customers.map((customer, rank) => {
    const cumulative = customers.slice(0, rank + 1).reduce((sum, item) => sum + item.adverse, 0)
    return {
      ...customer,
      rank,
      share: total ? customer.adverse / total * 100 : 0,
      cumulativeShare: total ? cumulative / total * 100 : 0,
    }
  })
  const cutoffIndex = chartData.findIndex((customer) => customer.cumulativeShare >= 90)
  const protectedCustomers = chartData.slice(0, cutoffIndex + 1).map((customer) => customer.name)

  return (
    <article className="panel pareto-panel"><div className="panel-heading"><div><div className="eyebrow">commercial transmission</div><h3>Where the dollars land</h3></div><span className="panel-tag">cumulative exposure / {customers.length} accounts</span></div><div className="pareto-chart"><Suspense fallback={<div className="chart-fallback">Loading cumulative exposure chart…</div>}><Charts activeCustomer={activeCustomer} data={chartData} kind="pareto" setActiveCustomer={setActiveCustomer} /></Suspense></div><div className="pareto-legend"><span><i className="pareto-bar-key" /> account share</span><span><i className="pareto-line-key" /> cumulative exposure</span><span><i className="pareto-cutoff-key" /> 90% cutoff</span></div><div className="pareto-callout"><Icon name="target" size={16} /><span><b>90% cutoff:</b> protect {protectedCustomers.join(' + ')}; manage the tail by rule.</span></div></article>
  )
}

function VulnerabilityMap({ activeCustomer, setActiveCustomer }) {
  const visibleCustomers = customers
  const max = Math.max(...visibleCustomers.map((customer) => customer.adverse))
  const chartData = visibleCustomers.map((customer) => ({ ...customer }))
  return (
    <article className="panel map-panel"><div className="panel-heading"><div><div className="eyebrow">impact × rate severity</div><h3>Scale does not equal severity</h3></div><div className="chart-focus"><label htmlFor="map-focus">keyboard focus</label><select id="map-focus" aria-label="Select customer on impact map" onChange={(event) => setActiveCustomer(event.target.value)} value={activeCustomer}>{customers.map((customer) => <option key={customer.name} value={customer.name}>{customer.name}</option>)}<option value="">Portfolio view</option></select></div></div><div className="map-legend"><span><i className="legend-dot blue" /> y = positive adverse sensitivity $</span><span><i className="legend-dot amber" /> selected customer</span></div><div className="scatter-chart"><Suspense fallback={<div className="chart-fallback">Loading impact map…</div>}><Charts activeCustomer={activeCustomer} data={chartData} kind="vulnerability" max={max} setActiveCustomer={setActiveCustomer} /></Suspense></div><div className="map-footer"><span>Bubble size = full contracted revenue</span><span>Keyboard selector syncs with chart focus</span></div></article>
  )
}

function ScorePanel({ scoreLens, setScoreLens }) {
  const rows = scoreRows[scoreLens]
  const lattice = scoreRobustness[scoreLens]
  const stableTopTwo = lattice.rows.filter((row) => row.topTwoShare === 100).slice(0, 2).map((row) => row.name).join(' + ')

  return (
    <article className="panel score-panel"><div className="panel-heading"><div><div className="eyebrow">appendix diagnostic / ordinal priority</div><h3>Score the mechanism, not the decision</h3></div><div className="score-tabs">{Object.keys(scoreRows).map((lens) => <button className={scoreLens === lens ? 'active' : ''} key={lens} onClick={() => setScoreLens(lens)} type="button">{lens}</button>)}</div></div><div className="score-table-wrap"><table className="score-table"><thead><tr><th>rank / segment</th><th>score</th><th>adverse $</th><th>M · cost severity</th><th>I · insurance</th><th>D · delay cost</th><th>C · dependence</th><th>exact-grain flags</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.name}><td><span className="score-name"><b>{String(index + 1).padStart(2, '0')}</b>{row.name}</span><small>{row.sample} shipments</small></td><td><span className="score-number">{row.score}</span><span className="score-progress"><i style={{ width: `${row.score}%` }} /></span></td><td className="money-cell">{money(row.adverse)}</td><td>{percent(row.M)}</td><td>{percent(row.I, 2)}</td><td>{percent(row.D, 1)}</td><td>{percent(row.C)}</td><td>{row.flags?.map((flag) => <span className="flag-pill" key={flag}>{flag}</span>) || <span className="na">—</span>}</td></tr>)}</tbody></table></div><div className="score-note"><Icon name="layers" size={15} /> Legacy diagnostic only; dollars and hard flags drive the action table. {lattice.vectors}-vector lattice: {stableTopTwo || 'no universal top-two pair'} stable in {scoreLens.toLowerCase()}.</div></article>
  )
}

function ActionCells() {
  const [customerFilter, setCustomerFilter] = useState('all')
  const [routeFilter, setRouteFilter] = useState('all')
  const [kindFilter, setKindFilter] = useState('all')
  const customersInCells = [...new Set(cells.map((cell) => cell.customer))].sort()
  const routesInCells = [...new Set(cells.map((cell) => cell.route))].sort()
  const filtered = cells.filter((cell) => (customerFilter === 'all' || cell.customer === customerFilter) && (routeFilter === 'all' || cell.route === routeFilter) && (kindFilter === 'all' || cell.kind === kindFilter))

  return (
    <article className="panel cell-panel"><div className="panel-heading"><div><div className="eyebrow">master action table / {cells.length} observed cells</div><h3>Every material decision has a cell.</h3></div><div className="cell-filters"><label>customer<select aria-label="Filter cells by customer" onChange={(event) => setCustomerFilter(event.target.value)} value={customerFilter}><option value="all">all customers</option>{customersInCells.map((customer) => <option key={customer}>{customer}</option>)}</select></label><label>route / status<select aria-label="Filter cells by route" onChange={(event) => setRouteFilter(event.target.value)} value={routeFilter}><option value="all">all states</option>{routesInCells.map((route) => <option key={route}>{route}</option>)}</select></label><label>universe<select aria-label="Filter cells by universe" onChange={(event) => setKindFilter(event.target.value)} value={kindFilter}><option value="all">all</option><option value="delivered">delivered</option><option value="held">held</option></select></label></div></div><div className="table-wrap cell-table-wrap"><table className="cell-table"><thead><tr><th>customer</th><th>product</th><th>route / status</th><th>n</th><th>contracted</th><th>recognized</th><th>positive / signed sensitivity</th><th>zero-margin / benchmark surcharge</th><th>DIFOT</th><th>Held age / revenue</th><th>hard flags</th><th>action / owner</th><th>trigger</th></tr></thead><tbody>{filtered.map((cell) => <tr key={`${cell.customer}-${cell.product}-${cell.route}`}><td>{cell.customer}</td><td>{cell.product}</td><td><span className={`cell-state ${cell.kind}`}>{cell.route}</span></td><td>{cell.shipments}{cell.shipments < 3 && <small className="sample-warning">low sample</small>}</td><td className="money-cell">{money(cell.contracted)}</td><td className="money-cell">{money(cell.recognized)}</td><td><span className="cell-pair"><b>{money(cell.adverse)}</b><small>{money(cell.signedSensitivity)} signed</small></span></td><td><span className="cell-pair"><b>{money(cell.zeroMarginSurcharge)}</b><small>{money(cell.benchmarkPreservingSurcharge)} benchmark</small></span></td><td>{cell.difot == null ? <span className="na">n.a.</span> : `${percent(cell.difot)} (${cell.difotHits}/${cell.difotDenominator})`}</td><td>{cell.kind === 'held' ? <span className="cell-pair"><b>{cell.heldAgeDays.toLocaleString()}d</b><small>{money(cell.heldRevenue)} revenue</small></span> : <span className="na">n.a.</span>}</td><td>{cell.flags.map((flag) => <span className="flag-pill" key={flag}>{flag}</span>)}</td><td><span className="cell-pair"><b>{cell.action}</b><small>{cell.owner}</small></span></td><td>{cell.trigger}</td></tr>)}</tbody></table></div><div className="panel-footnote"><span className="dot dot-amber" /> Low-sample cells remain visible; absence of an observed route is not treated as proof of infeasibility.</div></article>
  )
}

function ProductFrontier() {
  return (
    <article className="panel frontier-panel"><div className="panel-heading"><div><div className="eyebrow">product-matched route frontier</div><h3>Compare like cargo before changing the lane.</h3></div><span className="panel-tag">observational pilot evidence</span></div><div className="table-wrap"><table className="frontier-table"><thead><tr><th>product</th><th>preferred observed route</th><th>comparison route</th><th>cost / t</th><th>DIFOT / raw n / 90% interval</th><th>decision status</th></tr></thead><tbody>{frontier.map((row) => <tr key={row.product}><td><b>{row.product}</b></td><td>{row.preferred}</td><td>{row.compared || <span className="na">not observed</span>}</td><td>{perTon(row.preferredCostPerTon)} vs {perTon(row.comparedCostPerTon)}</td><td>{percent(row.preferredDifot)} ({row.preferredSample}) [{percent(row.preferredInterval?.lower)}–{percent(row.preferredInterval?.upper)}]<br /><span className="faint-line">vs {percent(row.comparedDifot)} ({row.comparedSample || 'n.a.'}) [{percent(row.comparedInterval?.lower)}–{percent(row.comparedInterval?.upper)}]</span></td><td><span className="option-chip">{row.status}</span></td></tr>)}</tbody></table></div><div className="panel-footnote"><span className="dot dot-amber" /> Better observed cost and DIFOT support a controlled pilot, not a causal claim that rerouting would reproduce the result.</div></article>
  )
}

function HeldQueue() {
  return (
    <article className="panel queue-panel"><div className="panel-heading"><div><div className="eyebrow">open exposure / release ledger</div><h3>Held is a queue, not a route</h3></div><span className="status-pill red"><i />{controls.heldRows} shipments open</span></div><div className="queue-stats"><div><span>unlock</span><b>{money(controls.heldRevenue)}</b></div><div><span>cost accrued</span><b>{money(controls.heldCost)}</b></div><div><span>penalties</span><b>{money(controls.heldPenalty)}</b></div><div><span>median / p90 / max</span><b>{controls.heldMedianDays}d / {controls.heldP90Days.toFixed(0)}d / {controls.heldMaxDays}d</b></div></div><div className="table-wrap"><table className="queue-table"><thead><tr><th>shipment / account</th><th>product</th><th>age</th><th>historical penalty / day</th><th>revenue unlock</th><th>next gate</th></tr></thead><tbody>{heldQueue.map((row) => <tr key={row.id}><td><b>{row.id}</b><small>{row.customer}</small></td><td>{row.product}</td><td><span className="age-badge">{row.days}d</span></td><td className="money-cell">{money(row.penaltyPerDay, 3)}</td><td className="money-cell">{money(row.revenue, 2)}</td><td><span className="option-chip">{row.option}</span></td></tr>)}</tbody></table></div><div className="queue-footer"><span><Icon name="pulse" size={15} /> Sorted by observed penalty/day, then revenue unlock.</span><strong>Run-rate is historical; forward quote required before release.</strong></div></article>
  )
}

function ScenarioPanel({ activeScenario, setActiveScenario, scenarioInputs, setScenarioInputs }) {
  const selected = scenarios[activeScenario]
  const inputs = scenarioInputs[selected.name]
  const approvedInputsMatch = Object.keys(selected.inputs).every((key) => JSON.stringify(inputs[key]) === JSON.stringify(selected.inputs[key]))
  const approvedModel = selected.decisionReady && selected.outputs?.locked === false && approvedInputsMatch
  const output = approvedModel ? selected.outputs : calculateScenario(inputs)
  const fields = [
    ['costMultiplier', 'cost ×', 'Procurement / Finance', 0, 3, 0.05],
    ['insuranceMultiplier', 'insurance ×', 'CRO / Finance', 0, 3, 0.05],
    ['penaltyMultiplier', 'penalty ×', 'Operations / Finance', 0, 3, 0.05],
    ['clearRate', 'clear rate', 'COO / Network Planning', 0, 1, 0.05],
    ['heldInflowMultiplier', 'Held inflow ×', 'COO / Network Planning', 0, 3, 0.05],
    ['recoveryRate', 'recovery rate', 'CCO / Legal', 0, 1, 0.05],
    ['serviceMultiplier', 'service ×', 'Operations', 0, 2, 0.05],
  ]
  const updateInput = (key, value) => setScenarioInputs((current) => ({ ...current, [selected.name]: { ...current[selected.name], [key]: value } }))
  const resetInputs = () => setScenarioInputs((current) => ({ ...current, [selected.name]: { ...selected.inputs } }))
  const deliveredRoutes = routes.filter((route) => route.kind === 'delivered')

  return (
    <article className="panel scenario-panel">
      <div className="panel-heading">
        <div><div className="eyebrow">stage 07 / owner-editable decision stress</div><h3>Three scenarios. Numeric gates.</h3></div>
        <span className="panel-tag">browser inputs / not yet live</span>
      </div>
      <div className="scenario-grid">
        {scenarios.map((scenario, index) => <button className={`scenario-card ${scenario.tone} ${activeScenario === index ? 'active' : ''}`} key={scenario.name} onClick={() => setActiveScenario(index)} type="button"><span className="scenario-index">0{index + 1}</span><b>{scenario.name}</b><p>{scenario.detail}</p><span className="scenario-action">{scenario.action}</span></button>)}
      </div>
      <div className="scenario-input-panel">
        <div className="scenario-input-heading"><div><span className="eyebrow">owner inputs / {selected.name}</span><p>Queue controls update the safe flow. Economic fields are retained for the approved forward ledger and do not create board outputs here.</p></div><button className="text-button" onClick={resetInputs} type="button">Reset proposal defaults</button></div>
        <div className="scenario-inputs">{fields.map(([key, label, owner, min, max, step]) => <label key={key}><span>{label}<small>{owner}</small></span><input max={max} min={min} onChange={(event) => updateInput(key, Number(event.target.value))} step={step} type="number" value={inputs[key]} /></label>)}</div>
        <div className="scenario-routes"><span>unavailable routes <small>Network Planning</small></span>{deliveredRoutes.map((route) => <label key={route.name}><input checked={inputs.unavailableRoutes.includes(route.name)} onChange={() => updateInput('unavailableRoutes', inputs.unavailableRoutes.includes(route.name) ? inputs.unavailableRoutes.filter((item) => item !== route.name) : [...inputs.unavailableRoutes, route.name])} type="checkbox" />{route.name}</label>)}</div>
      </div>
      <div className={`scenario-detail ${selected.tone}`}>
        <div>
          <span className="eyebrow">{approvedModel ? `approved forward ledger / ${selected.name}` : `safe queue flow / ${selected.name}`}</span>
          <div className="scenario-output-grid">
            {approvedModel ? <><span><small>forward contribution</small><b>{money(output.totalContribution)}</b></span><span><small>cleared Held revenue</small><b>{money(output.clearedRevenue)}</b></span><span><small>ending Held revenue</small><b>{money(output.endingHeldRevenue)}</b></span><span><small>forward DIFOT</small><b>{percent(output.difot)}</b></span></> : <><span><small>opening Held revenue</small><b>{money(output.beginningHeldRevenue)}</b></span><span><small>inflow Held revenue</small><b>{money(output.inflowRevenue)}</b></span><span><small>cleared Held revenue</small><b>{money(output.clearedRevenue)}</b></span><span><small>ending Held revenue</small><b>{money(output.endingHeldRevenue)}</b></span></>}
          </div>
        </div>
        <span className="scenario-detail-action"><Icon name={approvedModel ? 'arrow' : 'lock'} size={16} /> {approvedModel ? 'approved ledger vector' : 'board outputs locked'}</span>
      </div>
      {approvedModel ? <div className="scenario-subgrid"><div><small>route allocation</small><span>{output.routeAllocation.map((route) => <em key={route.route}>{route.route}: {percent(route.share)} ({Math.round(route.allocatedTonnes).toLocaleString()}t)</em>)}</span></div><div><small>ledger triggers</small><span>{output.triggerCrossings.length ? output.triggerCrossings.map((trigger) => <em className="trigger-chip" key={trigger}>{trigger}</em>) : <em className="clear-chip">none</em>}</span></div><div><small>forward constraints</small><span><em>ending Held {Math.round(output.endingHeldTonnes).toLocaleString()}t</em><em>DIFOT lower bound {percent(output.difot)}</em></span></div></div> : <div className="scenario-subgrid"><div><small>flow conservation</small><span><em>{Math.round(output.beginningHeldTonnes).toLocaleString()}t opening</em><em>+ {Math.round(output.inflowTonnes).toLocaleString()}t inflow</em><em>− {Math.round(output.clearedTonnes).toLocaleString()}t cleared</em><em>= {Math.round(output.endingHeldTonnes).toLocaleString()}t ending</em></span></div><div><small>safe release signals</small><span>{output.triggerCrossings.length ? output.triggerCrossings.map((trigger) => <em className="trigger-chip" key={trigger}>{trigger}</em>) : <em className="clear-chip">queue clears</em>}</span></div><div><small>decision gate</small><span><em className="trigger-chip">contribution locked</em><em className="trigger-chip">route allocation locked</em><em className="trigger-chip">DIFOT locked</em>{inputs.unavailableRoutes.map((route) => <em key={route}>unavailable: {route}</em>)}</span></div></div>}
      <div className="scenario-note">{approvedModel ? 'Approved forward ledger vector shown; rerun after any input change so the Python and React outputs remain on the same golden vector.' : 'Only the opening/inflow/cleared/ending queue flow is shown here. Contribution, route capacity/allocation and scenario DIFOT require the approved forward ledger; current source and owner-input gates are not ready.'}</div>
    </article>
  )
}

function ActionRegister() {
  return (
    <article className="panel action-panel"><div className="panel-heading"><div><div className="eyebrow">stage 08 / decision register</div><h3>Five moves with an owner and an exit</h3></div><span className="panel-tag">board-ready</span></div><div className="action-list">{actions.map((action) => <div className="action-row" key={action.priority}><span className="action-number">{action.priority}</span><div className="action-title"><small>{action.type}</small><b>{action.title}</b></div><div><small>owner</small><b>{action.owner}</b></div><div><small>horizon</small><b>{action.horizon}</b></div><div className="action-trigger"><small>activate when</small><span>{action.trigger}</span></div><div className="action-release"><small>release / reverse</small><span>{action.release}</span></div></div>)}</div><div className="action-footnote"><Icon name="shield" size={15} /> The strategic direction stays fixed; missing live inputs change the execution gate, not the decision.</div></article>
  )
}

function App() {
  const [activeCustomer, setActiveCustomer] = useState('')
  const [routeMode, setRouteMode] = useState('all')
  const [scoreLens, setScoreLens] = useState('Customer')
  const [activeScenario, setActiveScenario] = useState(0)
  const [scenarioInputs, setScenarioInputs] = useState(() => Object.fromEntries(scenarios.map((scenario) => [scenario.name, { ...scenario.inputs }])))
  const [showEvidence, setShowEvidence] = useState(false)
  const focus = useMemo(() => customers.find((customer) => customer.name === activeCustomer), [activeCustomer])
  const adverse = focus ? focus.adverse : controls.adverseSensitivity
  const contracted = focus ? focus.contracted : controls.contractedRevenue
  const held = focus ? focus.held : controls.heldRevenue
  const difot = focus ? focus.difot : controls.postDIFOT
  const heldShipments = focus ? focus.heldShipments : controls.heldRows
  const deliveredMisses = focus ? focus.deliveredMisses : controls.deliveredRows - controls.deliveredDIFOTHits
  const bridgeWidth = (value) => `${Math.min(100, Math.abs(value) / controls.contractedRevenue * 100)}%`

  return (
    <div className="app-shell"><aside className="sidebar"><div className="brand"><span className="brand-mark">S</span><div><strong>SOMAIYA</strong><small>network control</small></div></div><div className="sidebar-status"><span className="live-dot" /> War-room snapshot <b>R2</b></div><nav className="side-nav" aria-label="Dashboard sections"><a className="active" href="#command"><Icon name="compass" /> Command center</a><a href="#exposure"><Icon name="chart" /> Exposure map</a><a href="#queue"><Icon name="truck" /> Held queue <span>{controls.heldRows}</span></a><a href="#decisions"><Icon name="flag" /> Decisions <span>05</span></a></nav><div className="sidebar-bottom"><div className="source-card"><div className="eyebrow">evidence base</div><strong>Cleaned workbook</strong><span>{metadata.rawRows} raw → {metadata.canonicalRows} canonical</span><span>{dateLabel(metadata.observationStart)} — {dateLabel(metadata.observationEnd)}</span><small>Source gate unverified</small></div><div className="sidebar-footer"><span>QUANTIZ’26</span><span>generated / internal</span></div></div></aside>
      <main className="main-content"><header className="topbar"><div className="crumb"><span>R2</span><i>/</i> STRAIT OUTTA HORMUZ</div><div className="topbar-right"><span className="refresh"><i /> snapshot {dateLabel(metadata.asOf)}</span><label className="focus-select"><span>focus</span><select aria-label="Focus account" onChange={(event) => setActiveCustomer(event.target.value)} value={activeCustomer}><option value="">Portfolio view</option>{customers.map((customer) => <option key={customer.name} value={customer.name}>{customer.name}</option>)}</select></label></div></header><div className="provisional-banner"><span><Icon name="lock" size={15} /> PROVISIONAL — {metadata.canonicalRows}-row canonical view / raw gate unverified</span><button onClick={() => setShowEvidence(!showEvidence)} type="button">{showEvidence ? 'Hide' : 'Open'} source controls <Icon name="arrow" size={14} /></button></div>{showEvidence && <div className="evidence-drawer"><span><b>Source gate</b> {metadata.rawRows} raw → {metadata.canonicalRows} canonical; approved contract is 246 raw → 243 canonical ({metadata.sourceGate?.status}).</span><span><b>Safe treatment</b> no prorating, no manufactured rows, no raw concentration denominator.</span><span><b>Refresh gate</b> blank/conflicting IDs fail the refresh; duplicate adjudication is saved to analysis/duplicate-adjudication.json.</span></div>}
        <section className="hero section-pad" id="command"><div className="hero-copy"><div className="eyebrow">executive exposure bridge / {dateLabel(metadata.asOf)}</div><h1>The corridor still moves.<br /><em>The economics don’t.</em></h1><p>Hormuz shock → operating vulnerability → commercial transmission → dollars at risk → an executable response.</p><div className="hero-actions"><a className="primary-button" href="#decisions">Open decision register <Icon name="arrow" size={16} /></a><a className="text-button" href="#controls">Read treatment rules <Icon name="arrow" size={15} /></a></div></div><div className="shock-chain"><div className="chain-line" /><div className="chain-node"><span>01</span><b>Hormuz shock</b><small>Direct closed as an option</small></div><div className="chain-node"><span>02</span><b>Open exposure</b><small>{controls.heldRows} Held / {money(controls.heldRevenue)} unrecognized</small></div><div className="chain-node"><span>03</span><b>Business problem</b><small>{money(controls.adverseSensitivity)} positive sensitivity</small></div><div className="chain-node active"><span>04</span><b>Move now</b><small>Release → reprice → redesign</small></div></div></section>
        <section className="metric-grid section-pad" aria-label="Portfolio controls"><MetricCard icon="database" label="Contracted freight revenue" value={money(contracted)} meta={focus ? `${percent(focus.fullShare)} full-portfolio share · KPI focus only` : `${money(controls.recognizedRevenue)} recognized • ${money(controls.heldRevenue)} held`} tone="blue" /><MetricCard icon="trend" label="Positive adverse sensitivity" value={money(adverse)} meta={focus ? `${percent(focus.severity)} of focused shock revenue` : `${percent(controls.adverseSensitivity / (controls.contractedRevenue - controls.heldRevenue) * 100)} of post-blockade revenue`} tone="red" /><MetricCard icon="lock" label="Held contracted revenue" value={money(held)} meta={focus ? `${heldShipments} focused Held shipments` : `${controls.heldRows} shipments • ${controls.heldDays.toLocaleString()} days stuck`} tone="amber" /><MetricCard icon="pulse" label="Post-blockade DIFOT" value={percent(difot)} meta={focus ? `${deliveredMisses} misses / ${focus.deliveredShipments} delivered` : `${deliveredMisses} misses / ${controls.deliveredRows} delivered • vs ${percent(controls.directDIFOT)} Direct`} tone="mint" /></section>
        <section className="section-pad" id="exposure"><SectionHeader eyebrow="01 / exposure bridge" title="The loss is transmitted in two ways." copy={focus ? `Account lens: ${focus.name}. Focus changes KPI cards only; every bridge, table and chart remains the portfolio control.` : 'A delivered margin shock and an open revenue queue. Keep them visible without double counting.'} action={<span className="section-stamp"><Icon name="shield" size={15} /> no double count</span>} /><div className="bridge-grid"><article className="panel financial-panel"><div className="panel-heading"><div><div className="eyebrow">financial transmission</div><h3>Contracted value → changed cost-to-serve</h3></div><span className="panel-tag">{money(controls.contractedRevenue)} portfolio</span></div><div className="bridge-chart"><div className="bridge-row"><span>contracted revenue</span><b>{money(controls.contractedRevenue)}</b><div className="bridge-bar"><i className="blue-fill" style={{ width: '100%' }} /></div></div><div className="bridge-row"><span>recognized revenue</span><b>{money(controls.recognizedRevenue)}</b><div className="bridge-bar"><i className="mint-fill" style={{ width: bridgeWidth(controls.recognizedRevenue) }} /></div></div><div className="bridge-row"><span>held / not recognized</span><b className="amber-text">−{money(controls.heldRevenue)}</b><div className="bridge-bar"><i className="amber-fill" style={{ width: bridgeWidth(controls.heldRevenue) }} /></div></div><div className="bridge-row"><span>observed delivered contribution</span><b className="red-text">{money(controls.deliveredMargin)}</b><div className="bridge-bar negative"><i className="red-fill" style={{ width: bridgeWidth(controls.deliveredMargin) }} /></div></div></div><div className="bridge-summary"><div><small>Direct-equivalent contribution</small><b className="mint-text">+{money(controls.deliveredBenchmarkContribution)}</b></div><div><small>Signed delivered sensitivity</small><b className="red-text">−{money(controls.deliveredSignedSensitivity)}</b></div><div><small>Observed delivered margin</small><b className="red-text">{money(controls.deliveredMargin)}</b></div></div><p className="panel-footnote">Insurance and penalties are already inside total cost-to-serve; they explain the mechanism, not an extra loss line.</p></article><RouteTable mode={routeMode} setMode={setRouteMode} /></div></section>
        <section className="section-pad"><SectionHeader eyebrow="02 / commercial transmission" title="Protect the dollars first. Diagnose the severity second." copy="Pareto uses the full shock denominator. The map keeps rate severity from disappearing behind account scale." /><div className="exposure-grid"><CustomerPareto activeCustomer={activeCustomer} setActiveCustomer={setActiveCustomer} /><VulnerabilityMap activeCustomer={activeCustomer} setActiveCustomer={setActiveCustomer} /></div></section>
        <section className="section-pad"><SectionHeader eyebrow="03 / score decomposition" title="A score can prioritize treatment. It cannot replace the dollars." copy="Within-universe ordinal index only. Flags override a favourable average score." /><ScorePanel scoreLens={scoreLens} setScoreLens={setScoreLens} /></section>
        <section className="section-pad"><SectionHeader eyebrow="04 / decision grain" title="Move from aggregates to the exact cell." copy={`All ${cells.length} observed customer × product × route/status cells reconcile to the generated controls. Filter the operating decision, not just the chart.`} /><ActionCells /></section>
        <section className="section-pad"><SectionHeader eyebrow="05 / matched operating frontier" title="Change lanes only inside a comparable product set." copy="Observed route differences are a pilot hypothesis. Service intervals keep small samples from looking like certainty." /><ProductFrontier /></section>
        <section className="section-pad" id="queue"><SectionHeader eyebrow="06 / operating response" title="Stop holding by default." copy="Held shipments have no actual transit by design. Release them by observed penalty run-rate, revenue unlock, feasibility and service window." action={<span className="risk-badge"><i /> open exposure</span>} /><HeldQueue /></section>
        <section className="section-pad"><SectionHeader eyebrow="07 / next disruption" title="Stress the queue, not the spreadsheet." copy="Owner-editable inputs recalculate a conserved Held flow. Contribution, route allocation and scenario DIFOT stay locked until the source and forward-input gates pass." /><ScenarioPanel activeScenario={activeScenario} scenarioInputs={scenarioInputs} setActiveScenario={setActiveScenario} setScenarioInputs={setScenarioInputs} /></section>
        <section className="section-pad" id="decisions"><SectionHeader eyebrow="08 / action register" title="Protect. Change. Stop." copy="Every move has one accountable owner, a horizon, an activation trigger and a release metric." /><ActionRegister /></section>
        <section className="section-pad controls-section" id="controls"><SectionHeader eyebrow="09 / controls & exclusions" title="The rules that keep this war room honest." copy="These are the guardrails behind every headline above." action={<span className="section-stamp"><Icon name="database" size={15} /> generated data spine</span>} /><div className="control-grid"><div className="control-card"><Icon name="database" size={18} /><b>Raw → canonical gate</b><p>{metadata.rawRows} raw rows currently produce {metadata.canonicalRows} canonical rows. Strict acceptance requires the approved 246-row source, three excess duplicate rows, hash and adjudication table.</p></div><div className="control-card"><Icon name="layers" size={18} /><b>Universe split</b><p>Direct = historical benchmark. Shock = everything else. Held is open exposure, not delivered economics.</p></div><div className="control-card"><Icon name="target" size={18} /><b>Ratio discipline</b><p>Aggregate numerators and denominators first. Never average row-level percentages or use stored concentration.</p></div><div className="control-card"><Icon name="compass" size={18} /><b>Feasibility first</b><p>Pipeline observed for bulk; Air and Overland for containers; Cape observed for both. Absence is not proof.</p></div><div className="control-card"><Icon name="pulse" size={18} /><b>Correlation warning</b><p>Observed route differences support matched pilots and gates, not causal claims about what another route would have done.</p></div><div className="control-card"><Icon name="shield" size={18} /><b>Emergency mode</b><p>Air and Overland are priced against fixed ocean-rate contracts. Judge the premium by recovery, criticality and avoided loss.</p></div><div className="control-card"><Icon name="target" size={18} /><b>Concentration diagnostic</b><p>Customer HHI {concentration.customerRevenue.hhi.toFixed(3)} ({concentration.customerRevenue.effectiveNumber.toFixed(2)} effective customers); route HHI {concentration.routeSensitivity.hhi.toFixed(3)}.</p></div></div></section>
        <footer className="app-footer"><span>QUANTIZ’26 / STRAIT OUTTA HORMUZ</span><span>Internal decision cockpit · provisional controls · {metadata.rawRows} raw → {metadata.canonicalRows} canonical</span><span>{dateLabel(metadata.observationStart).toUpperCase()} — {dateLabel(metadata.observationEnd).toUpperCase()}</span></footer>
      </main>
    </div>
  )
}

export default App
