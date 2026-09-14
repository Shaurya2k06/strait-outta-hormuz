import { useMemo, useState } from 'react'
import {
  actions,
  controls,
  customers,
  heldQueue,
  products,
  routes,
  scenarios,
  scoreRows,
} from './data'
import './App.css'

const money = (value, digits = 1) => `$${Number(value).toFixed(digits)}M`
const percent = (value, digits = 1) => (value == null ? 'n.a.' : `${Number(value).toFixed(digits)}%`)

function Icon({ name, size = 18 }) {
  const paths = {
    arrow: <path d="M5 12h13m-6-6 6 6-6 6" />,
    chart: <path d="M4 19V5m0 14h16M8 15v-3m4 3V8m4 7V5" />,
    compass: <path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6L12 3Z" />,
    database: <path d="M5 6c0-1.7 3.1-3 7-3s7 1.3 7 3-3.1 3-7 3-7-1.3-7-3Zm0 0v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6m-14 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />,
    flag: <path d="M5 21V4m0 0c4-3 7 3 13 0v9c-6 3-9-3-13 0" />,
    layers: <path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5" />,
    lock: <path d="M6 10h12v10H6zM8 10V7a4 4 0 0 1 8 0v3" />,
    menu: <path d="M4 6h16M4 12h16M4 18h16" />,
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
  const rows = routes.filter((route) => mode === 'all' || (mode === 'delivered' ? route.kind !== 'held' : route.kind === 'held'))

  return (
    <article className="panel route-panel">
      <div className="panel-heading compact-heading"><div><div className="eyebrow">operating state</div><h3>Six states. One open queue.</h3></div><div className="segmented" role="group" aria-label="Route state filter">{['all', 'delivered', 'held'].map((item) => <button className={mode === item ? 'active' : ''} key={item} onClick={() => setMode(item)} type="button">{item}</button>)}</div></div>
      <div className="table-wrap"><table className="route-table"><thead><tr><th>state</th><th>shipments</th><th>DIFOT</th><th>cost / t</th><th>adverse $</th><th>delay / age</th></tr></thead><tbody>{rows.map((route) => <tr className={`row-${route.kind}`} key={route.name}><td><span className="state-name"><i />{route.name}</span></td><td>{route.shipments}</td><td>{route.difot == null ? <span className="na">open</span> : percent(route.difot)}</td><td>${route.costPerTon.toLocaleString()}</td><td className="money-cell">{money(route.adverse)}</td><td>{route.kind === 'held' ? `${route.delay.toLocaleString()}d` : `${route.delay}d`}</td></tr>)}</tbody></table></div>
      <div className="panel-footnote"><span className="dot dot-amber" /> Direct is a historical benchmark; Held is not a completed route.</div>
    </article>
  )
}

function CustomerPareto({ activeCustomer, setActiveCustomer }) {
  const max = Math.max(...customers.map((customer) => customer.adverse))
  const total = customers.reduce((sum, customer) => sum + customer.adverse, 0)

  return (
    <article className="panel pareto-panel"><div className="panel-heading"><div><div className="eyebrow">commercial transmission</div><h3>Where the dollars land</h3></div><span className="panel-tag">top 5 accounts</span></div><div className="pareto-list">{customers.map((customer, index) => { const cumulative = customers.slice(0, index + 1).reduce((sum, item) => sum + item.adverse, 0); const cumulativeShare = (cumulative / total) * 100; const active = activeCustomer === customer.name; return <button className={`pareto-row ${active ? 'selected' : ''}`} key={customer.name} onClick={() => setActiveCustomer(active ? '' : customer.name)} type="button"><span className="rank">0{index + 1}</span><span className="pareto-main"><span className="pareto-label"><b>{customer.name}</b><em>{percent(customer.fullShare)} portfolio share</em></span><span className="bar-line"><span style={{ width: `${(customer.adverse / max) * 100}%` }} /></span></span><span className="pareto-value">{money(customer.adverse)}<small>{percent(cumulativeShare)} cum.</small></span></button> })}</div><div className="pareto-callout"><Icon name="target" size={16} /> Meridian + Zenith + Pacific capture 90.4% of positive shock sensitivity.</div></article>
  )
}

function VulnerabilityMap({ activeCustomer, setActiveCustomer }) {
  const max = Math.max(...customers.map((customer) => customer.adverse))
  const labels = ['Meridian', 'Zenith', 'Pacific', 'Nordholm', 'Baltic']
  return (
    <article className="panel map-panel"><div className="panel-heading"><div><div className="eyebrow">value × vulnerability</div><h3>Scale does not equal severity</h3></div><span className="panel-tag">click a bubble to focus</span></div><div className="map-legend"><span><i className="legend-dot blue" /> adverse sensitivity $</span><span><i className="legend-dot amber" /> vulnerability score lens</span></div><svg aria-label="Customer value versus vulnerability map" className="scatter" role="img" viewBox="0 0 560 280"><line className="axis" x1="48" x2="530" y1="238" y2="238" /><line className="axis" x1="48" x2="48" y1="24" y2="238" /><line className="grid-line" x1="48" x2="530" y1="185" y2="185" /><line className="grid-line" x1="48" x2="530" y1="132" y2="132" /><line className="grid-line" x1="48" x2="530" y1="79" y2="79" /><text className="axis-label" x="48" y="263">0%</text><text className="axis-label" x="482" y="263">400% severity →</text><text className="axis-label" transform="rotate(-90)" x="-224" y="16">positive adverse $</text>{customers.map((customer, index) => { const x = 55 + Math.min(customer.severity, 400) / 400 * 460; const y = 226 - customer.adverse / max * 185; const radius = 8 + Math.sqrt(customer.contracted) * 2.1; const active = activeCustomer === customer.name; const activate = () => setActiveCustomer(active ? '' : customer.name); return <g className={`bubble ${active ? 'active' : ''}`} key={customer.name} onClick={activate} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate() } }} role="button" tabIndex="0"><circle cx={x} cy={y} r={radius} /><text x={Math.min(x + 10, 460)} y={y - 10}>{labels[index]}</text></g> })}</svg><div className="map-footer"><span>Bubble size = contracted revenue</span><span>Severity = positive sensitivity ÷ contracted revenue</span></div></article>
  )
}

function ScorePanel({ scoreLens, setScoreLens }) {
  const rows = scoreRows[scoreLens]
  const lookup = scoreLens === 'Customer' ? customers : scoreLens === 'Product' ? products : routes
  const getRaw = (row) => lookup.find((item) => item.name === row.name)

  return (
    <article className="panel score-panel"><div className="panel-heading"><div><div className="eyebrow">exposure score / ordinal priority</div><h3>Score the mechanism, not the outcome</h3></div><div className="score-tabs">{Object.keys(scoreRows).map((lens) => <button className={scoreLens === lens ? 'active' : ''} key={lens} onClick={() => setScoreLens(lens)} type="button">{lens}</button>)}</div></div><div className="score-table-wrap"><table className="score-table"><thead><tr><th>rank / segment</th><th>score</th><th>M · cost severity</th><th>I · insurance</th><th>D · delay cost</th><th>C · dependence</th><th>flags</th></tr></thead><tbody>{rows.map((row, index) => { const raw = getRaw(row); return <tr key={row.name}><td><span className="score-name"><b>0{index + 1}</b>{row.name}</span><small>{row.sample} shipments</small></td><td><span className="score-number">{row.score}</span><span className="score-progress"><i style={{ width: `${row.score}%` }} /></span></td><td>{percent(row.M)}</td><td>{percent(row.I, 2)}</td><td>{percent(row.D, 1)}</td><td>{percent(row.C)}</td><td>{raw?.flags?.map((flag) => <span className="flag-pill" key={flag}>{flag}</span>) || <span className="na">—</span>}</td></tr> })}</tbody></table></div><div className="score-note"><Icon name="layers" size={15} /> 45% M + 15% I + 20% D + 20% C. Scores are within-universe only; raw dollars stay beside them.</div></article>
  )
}

function HeldQueue() {
  return (
    <article className="panel queue-panel"><div className="panel-heading"><div><div className="eyebrow">open exposure / release ledger</div><h3>Held is a queue, not a route</h3></div><span className="status-pill red"><i />54 shipments open</span></div><div className="queue-stats"><div><span>unlock</span><b>{money(controls.heldRevenue / 1000000)}</b></div><div><span>cost accrued</span><b>{money(controls.heldCost / 1000000)}</b></div><div><span>penalties</span><b>{money(controls.heldPenalty / 1000000)}</b></div><div><span>median / max</span><b>{controls.heldMedianDays}d / {controls.heldMaxDays}d</b></div></div><div className="table-wrap"><table className="queue-table"><thead><tr><th>shipment / account</th><th>product</th><th>age</th><th>penalty / day</th><th>revenue unlock</th><th>next gate</th></tr></thead><tbody>{heldQueue.map((row) => <tr key={row.id}><td><b>{row.id}</b><small>{row.customer}</small></td><td>{row.product}</td><td><span className="age-badge">{row.days}d</span></td><td className="money-cell">${row.penaltyPerDay.toLocaleString()}</td><td className="money-cell">{money(row.revenue, 2)}</td><td><span className="option-chip">{row.option}</span></td></tr>)}</tbody></table></div><div className="queue-footer"><span><Icon name="pulse" size={15} /> Prioritize by penalty per day + revenue unlock</span><strong>Release gate: Held &gt;5 days or &gt;5% of portfolio revenue</strong></div></article>
  )
}

function ScenarioPanel({ activeScenario, setActiveScenario }) {
  const selected = scenarios[activeScenario]
  return (
    <article className="panel scenario-panel"><div className="panel-heading"><div><div className="eyebrow">stage 07 / decision stress</div><h3>No invented probability. Three live gates.</h3></div><span className="panel-tag">scenario control</span></div><div className="scenario-grid">{scenarios.map((scenario, index) => <button className={`scenario-card ${scenario.tone} ${activeScenario === index ? 'active' : ''}`} key={scenario.name} onClick={() => setActiveScenario(index)} type="button"><span className="scenario-index">0{index + 1}</span><b>{scenario.name}</b><p>{scenario.detail}</p><span className="scenario-action">{scenario.action}</span></button>)}</div><div className={`scenario-detail ${selected.tone}`}><div><span className="eyebrow">selected stress / {selected.name}</span><p>Recompute: <strong>{selected.outputs}</strong></p></div><span className="scenario-detail-action"><Icon name="arrow" size={16} /> {selected.action}</span></div><div className="scenario-note">Operations owns feasibility, capacity, ETA and live quote. Commercial owns recoverable surcharge and avoided loss. Finance validates contribution.</div></article>
  )
}

function ActionRegister() {
  return (
    <article className="panel action-panel"><div className="panel-heading"><div><div className="eyebrow">stage 09 / decision register</div><h3>Five moves with an owner and an exit</h3></div><span className="panel-tag">board-ready</span></div><div className="action-list">{actions.map((action) => <div className="action-row" key={action.priority}><span className="action-number">{action.priority}</span><div className="action-title"><small>{action.type}</small><b>{action.title}</b></div><div><small>owner</small><b>{action.owner}</b></div><div><small>horizon</small><b>{action.horizon}</b></div><div className="action-trigger"><small>activate when</small><span>{action.trigger}</span></div><div className="action-release"><small>release / reverse</small><span>{action.release}</span></div></div>)}</div><div className="action-footnote"><Icon name="shield" size={15} /> The strategic direction stays fixed; missing live inputs change the execution gate, not the decision.</div></article>
  )
}

function App() {
  const [activeCustomer, setActiveCustomer] = useState('')
  const [routeMode, setRouteMode] = useState('all')
  const [scoreLens, setScoreLens] = useState('Customer')
  const [activeScenario, setActiveScenario] = useState(0)
  const [showEvidence, setShowEvidence] = useState(false)
  const focus = useMemo(() => customers.find((customer) => customer.name === activeCustomer), [activeCustomer])
  const adverse = focus ? focus.adverse : controls.adverseSensitivity / 1000000
  const contracted = focus ? focus.contracted : controls.contractedRevenue / 1000000
  const held = focus ? focus.held : controls.heldRevenue / 1000000
  const difot = focus ? focus.difot : controls.postDIFOT

  return (
    <div className="app-shell"><aside className="sidebar"><div className="brand"><span className="brand-mark">S</span><div><strong>SOMAIYA</strong><small>network control</small></div></div><div className="sidebar-status"><span className="live-dot" /> War room live <b>R2</b></div><nav className="side-nav" aria-label="Dashboard sections"><a className="active" href="#command"><Icon name="compass" /> Command center</a><a href="#exposure"><Icon name="chart" /> Exposure map</a><a href="#queue"><Icon name="truck" /> Held queue <span>54</span></a><a href="#decisions"><Icon name="flag" /> Decisions <span>05</span></a></nav><div className="sidebar-bottom"><div className="source-card"><div className="eyebrow">evidence base</div><strong>Cleaned workbook</strong><span>243 canonical rows</span><span>05 Jan — 22 Mar 2026</span><small>Provisional control set</small></div><div className="sidebar-footer"><span>QUANTIZ’26</span><span>v1.0 / internal</span></div></div></aside>
      <main className="main-content"><header className="topbar"><div className="crumb"><span>R2</span><i>/</i> STRAIT OUTTA HORMUZ</div><div className="topbar-right"><span className="refresh"><i /> refreshed 22 Mar 2026</span><label className="focus-select"><span>focus</span><select aria-label="Focus account" onChange={(event) => setActiveCustomer(event.target.value)} value={activeCustomer}><option value="">Portfolio view</option>{customers.map((customer) => <option key={customer.name} value={customer.name}>{customer.name}</option>)}</select></label></div></header><div className="provisional-banner"><span><Icon name="lock" size={15} /> PROVISIONAL — 243-row cleaned file</span><button onClick={() => setShowEvidence(!showEvidence)} type="button">{showEvidence ? 'Hide' : 'Open'} source controls <Icon name="arrow" size={14} /></button></div>{showEvidence && <div className="evidence-drawer"><span><b>Source gate</b> case states 246 rows; supplied workbook has 243 unique IDs.</span><span><b>Safe treatment</b> no prorating, no manufactured rows, no raw concentration denominator.</span><span><b>Refresh gate</b> rerun every headline after raw-source reconciliation.</span></div>}
        <section className="hero section-pad" id="command"><div className="hero-copy"><div className="eyebrow">executive exposure bridge / 22 march 2026</div><h1>The corridor still moves.<br /><em>The economics don’t.</em></h1><p>Hormuz shock → operating vulnerability → commercial transmission → dollars at risk → an executable response.</p><div className="hero-actions"><a className="primary-button" href="#decisions">Open decision register <Icon name="arrow" size={16} /></a><a className="text-button" href="#controls">Read treatment rules <Icon name="arrow" size={15} /></a></div></div><div className="shock-chain"><div className="chain-line" /><div className="chain-node"><span>01</span><b>Hormuz shock</b><small>Direct closed as an option</small></div><div className="chain-node"><span>02</span><b>Open exposure</b><small>54 Held / $25.9M unrecognized</small></div><div className="chain-node"><span>03</span><b>Business problem</b><small>$178.7M positive sensitivity</small></div><div className="chain-node active"><span>04</span><b>Move now</b><small>Release → reprice → redesign</small></div></div></section>
        <section className="metric-grid section-pad" aria-label="Portfolio controls"><MetricCard icon="database" label="Contracted freight revenue" value={money(contracted)} meta={focus ? `${focus.fullShare}% full-portfolio share` : '87.4M recognized • 25.9M held'} tone="blue" /><MetricCard icon="trend" label="Positive adverse sensitivity" value={money(adverse)} meta={focus ? `${percent(focus.severity)} of focused revenue` : '185.7% of post-blockade revenue'} tone="red" /><MetricCard icon="lock" label="Held contracted revenue" value={money(held)} meta={focus ? `${focus.shipments} focused shipments open` : '54 shipments • 1,234 days stuck'} tone="amber" /><MetricCard icon="pulse" label="Post-blockade DIFOT" value={percent(difot)} meta={focus ? `${focus.shipments - Math.round(focus.shipments * focus.difot / 100)} misses in focus` : 'vs 100.0% Direct benchmark'} tone="mint" /></section>
        <section className="section-pad" id="exposure"><SectionHeader eyebrow="01 / exposure bridge" title="The loss is transmitted in two ways." copy={focus ? `Account lens: ${focus.name}. KPI cards are focused; the bridge remains the portfolio control.` : 'A delivered margin shock and an open revenue queue. Keep them visible without double counting.'} action={<span className="section-stamp"><Icon name="shield" size={15} /> no double count</span>} /><div className="bridge-grid"><article className="panel financial-panel"><div className="panel-heading"><div><div className="eyebrow">financial transmission</div><h3>Contracted value → changed cost-to-serve</h3></div><span className="panel-tag">$113.3M portfolio</span></div><div className="bridge-chart"><div className="bridge-row"><span>contracted revenue</span><b>$113.3M</b><div className="bridge-bar"><i className="blue-fill" style={{ width: '100%' }} /></div></div><div className="bridge-row"><span>recognized revenue</span><b>$87.4M</b><div className="bridge-bar"><i className="mint-fill" style={{ width: '77.1%' }} /></div></div><div className="bridge-row"><span>held / not recognized</span><b className="amber-text">−$25.9M</b><div className="bridge-bar"><i className="amber-fill" style={{ width: '22.9%' }} /></div></div><div className="bridge-row"><span>observed delivered contribution</span><b className="red-text">−$157.7M</b><div className="bridge-bar negative"><i className="red-fill" style={{ width: '92%' }} /></div></div></div><div className="bridge-summary"><div><small>Direct-equivalent contribution</small><b className="mint-text">+$8.3M</b></div><div><small>Signed sensitivity</small><b className="red-text">−$166.0M</b></div><div><small>Observed delivered margin</small><b className="red-text">−$157.7M</b></div></div><p className="panel-footnote">Insurance and penalties are already inside total cost-to-serve; they explain the mechanism, not an extra loss line.</p></article><RouteTable mode={routeMode} setMode={setRouteMode} /></div></section>
        <section className="section-pad"><SectionHeader eyebrow="02 / commercial transmission" title="Protect the dollars first. Diagnose the severity second." copy="Pareto sets board materiality. The bubble map keeps rate severity from disappearing behind account scale." /><div className="exposure-grid"><CustomerPareto activeCustomer={activeCustomer} setActiveCustomer={setActiveCustomer} /><VulnerabilityMap activeCustomer={activeCustomer} setActiveCustomer={setActiveCustomer} /></div></section>
        <section className="section-pad"><SectionHeader eyebrow="03 / score decomposition" title="A score can prioritize treatment. It cannot replace the dollars." copy="Within-universe ordinal index only. Flags override a favourable average score." /><ScorePanel scoreLens={scoreLens} setScoreLens={setScoreLens} /></section>
        <section className="section-pad" id="queue"><SectionHeader eyebrow="04 / operating response" title="Stop holding by default." copy="Held shipments have no actual transit by design. Release them by penalty run-rate, revenue unlock, feasibility and service window." action={<span className="risk-badge"><i /> open exposure</span>} /><HeldQueue /></section>
        <section className="section-pad"><SectionHeader eyebrow="05 / next disruption" title="Stress the decision, not the spreadsheet." copy="No unsupported probabilities. Change only live inputs that can move an action or cross a trigger." /><ScenarioPanel activeScenario={activeScenario} setActiveScenario={setActiveScenario} /></section>
        <section className="section-pad" id="decisions"><SectionHeader eyebrow="06 / action register" title="Protect. Change. Stop." copy="Every move has one accountable owner, a horizon, an activation trigger and a release metric." /><ActionRegister /></section>
        <section className="section-pad controls-section" id="controls"><SectionHeader eyebrow="07 / controls & exclusions" title="The rules that keep this war room honest." copy="These are the guardrails behind every headline above." /><div className="control-grid"><div className="control-card"><Icon name="database" size={18} /><b>Canonical grain</b><p>One surviving row per Shipment_ID. Current workbook passes at 243 rows; no duplicates to collapse.</p></div><div className="control-card"><Icon name="layers" size={18} /><b>Universe split</b><p>Direct = historical benchmark. Shock = everything else. Held is open exposure, not delivered economics.</p></div><div className="control-card"><Icon name="target" size={18} /><b>Ratio discipline</b><p>Aggregate numerators and denominators first. Never average row-level percentages or use stored concentration.</p></div><div className="control-card"><Icon name="compass" size={18} /><b>Feasibility first</b><p>Pipeline observed for bulk; Air and Overland for containers; Cape observed for both. Absence is not proof.</p></div><div className="control-card"><Icon name="pulse" size={18} /><b>Correlation warning</b><p>Observed route differences support matched pilots and gates, not causal claims about what another route would have done.</p></div><div className="control-card"><Icon name="shield" size={18} /><b>Emergency mode</b><p>Air and Overland are priced against fixed ocean-rate contracts. Judge the premium by recovery, criticality and avoided loss.</p></div></div></section>
        <footer className="app-footer"><span>QUANTIZ’26 / STRAIT OUTTA HORMUZ</span><span>Internal decision cockpit · provisional working controls · 243-row cleaned file</span><span>05 JAN — 22 MAR 2026</span></footer>
      </main>
    </div>
  )
}

export default App
