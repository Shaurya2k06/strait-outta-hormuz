import { useMemo, useState } from 'react'
import dashboardData from './data'
import './App.css'

const {
  appendixDiagnostics,
  customers,
  decisionCells,
  decisionRegister,
  financialBridge,
  heldLedger,
  metadata,
  methodology,
  portfolio,
  products,
  routeEvidence,
  routes,
  serviceEvidence,
  universes,
} = dashboardData

const formatMoney = (value, digits = 1) => {
  if (value == null) return 'open'
  const sign = Number(value) < 0 ? '−' : ''
  return `${sign}$${(Math.abs(Number(value)) / 1000000).toFixed(digits)}M`
}

const formatPercent = (value, digits = 1) => (value == null ? 'open' : `${Number(value).toFixed(digits)}%`)
const formatPerTon = (value) => (value == null ? 'open' : `$${Number(value).toFixed(2)}`)
const formatNumber = (value, digits = 0) => (value == null ? 'open' : Number(value).toLocaleString('en-US', { maximumFractionDigits: digits }))
const dateLabel = (value) => new Date(`${value}T00:00:00Z`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
const titleCase = (value) => value.replaceAll('_', ' ')
const routeLabel = (value) => value === 'Direct (Pre-Blockade)' ? 'Direct / benchmark' : value
const universeLabel = (value) => ({ direct_reference: 'Direct reference', post_blockade_delivered: 'Delivered', held_open: 'Held open' })[value] ?? value
const barWidth = (value) => `${Math.max(0, Math.min(100, Number(value) || 0))}%`

function EvidenceTag({ type }) {
  return <span className={`evidence-tag ${String(type).toLowerCase()}`}>{type}</span>
}

function StatusPill({ children, tone = 'neutral' }) {
  return <span className={`status-pill ${tone}`}><i />{children}</span>
}

function SectionHeading({ index, title, copy, action }) {
  return (
    <div className="section-heading">
      <div>
        <span className="section-index">{index}</span>
        <h2>{title}</h2>
        {copy && <p>{copy}</p>}
      </div>
      {action}
    </div>
  )
}

function Metric({ label, value, detail, tone = 'neutral' }) {
  return (
    <article className={`metric tone-${tone}`}>
      <div className="metric-label"><span>{label}</span><i /></div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  )
}

function BridgePanel() {
  return (
    <article className="panel bridge-panel">
      <div className="panel-heading">
        <div><span className="eyebrow">historical financial bridge</span><h3>Benchmark economics do not survive the route change.</h3></div>
        <EvidenceTag type="DERIVED" />
      </div>
      <div className="bridge-list">
        {financialBridge.steps.map((step) => (
          <div className={`bridge-item ${step.value < 0 ? 'negative' : ''}`} key={step.key}>
            <div className="bridge-item-top"><span>{step.label}</span><b>{formatMoney(step.value)}</b></div>
            <div className="bar-track"><i style={{ width: barWidth(step.displaySharePct) }} /></div>
          </div>
        ))}
      </div>
      <div className="bridge-callouts">
        <div><span>Direct-equivalent cost</span><b>{formatMoney(financialBridge.directEquivalentCost)}</b></div>
        <div><span>Benchmark contribution</span><b className="positive">+{formatMoney(financialBridge.benchmarkContribution)}</b></div>
        <div><span>Observed delivered contribution</span><b className="negative-text">{formatMoney(financialBridge.observedDeliveredContribution)}</b></div>
      </div>
      <p className="panel-note">The signed route-cost impact is a historical comparison against the supplied product-matched Direct benchmark. Insurance and penalty are already inside total cost-to-serve.</p>
    </article>
  )
}

function UniversePanel() {
  return (
    <article className="panel universe-panel">
      <div className="panel-heading">
        <div><span className="eyebrow">analytical universes</span><h3>Keep completed, benchmark and open records apart.</h3></div>
        <StatusPill tone="accepted">{portfolio.shipments} accepted</StatusPill>
      </div>
      <div className="universe-list">
        {Object.entries(universes).map(([key, item]) => (
          <div className="universe-row" key={key}>
            <div><b>{universeLabel(key)}</b><span>{item.use}</span></div>
            <strong>{item.rows}</strong>
            <EvidenceTag type={item.evidenceType} />
          </div>
        ))}
      </div>
      <div className="universe-foot"><span>Portfolio revenue identity</span><b>{formatMoney(portfolio.contractedRevenue, 2)} = {formatMoney(portfolio.recognizedRevenue, 2)} recognized + {formatMoney(portfolio.heldContractedRevenue, 2)} Held</b></div>
    </article>
  )
}

function ExposurePanel({ selectedCustomer, setSelectedCustomer }) {
  const topThree = customers[2]
  return (
    <article className="panel exposure-panel">
      <div className="panel-heading">
        <div><span className="eyebrow">positive route-cost exposure</span><h3>Dollar concentration sets the attention order.</h3></div>
        <label className="select-control">focus account<select aria-label="Focus customer" value={selectedCustomer} onChange={(event) => setSelectedCustomer(event.target.value)}><option value="">Portfolio</option>{customers.map((customer) => <option key={customer.name} value={customer.name}>{customer.name}</option>)}</select></label>
      </div>
      <div className="exposure-summary"><b>{formatMoney(portfolio.positiveSensitivity)}</b><span>positive sensitivity across {customers.length} shock accounts</span><em>Top three cumulative share: {formatPercent(topThree?.cumulativeSharePct, 1)}</em></div>
      <div className="exposure-table-wrap">
        <table className="exposure-table"><thead><tr><th>rank / customer</th><th>positive sensitivity</th><th>share</th><th>cumulative</th><th>shock sample</th><th>Held revenue</th></tr></thead><tbody>
          {customers.map((customer) => (
            <tr className={selectedCustomer === customer.name ? 'selected' : ''} key={customer.id} onClick={() => setSelectedCustomer(selectedCustomer === customer.name ? '' : customer.name)}>
              <td><span className="rank-name"><b>{String(customer.rank).padStart(2, '0')}</b>{customer.name}</span></td>
              <td className="money-cell">{formatMoney(customer.positiveSensitivity)}</td>
              <td><div className="share-cell"><span>{formatPercent(customer.exposureSharePct, 1)}</span><i><em style={{ width: barWidth(customer.exposureSharePct) }} /></i></div></td>
              <td>{formatPercent(customer.cumulativeSharePct, 1)}</td>
              <td>{customer.sample}</td>
              <td className="money-cell">{formatMoney(customer.heldRevenue)}</td>
            </tr>
          ))}
        </tbody></table>
      </div>
      <p className="panel-note">Positive sensitivity locates gross route-cost exposure. It is not labelled as an accounting loss and does not decide customer exit.</p>
    </article>
  )
}

function ProductPanel() {
  return (
    <article className="panel product-panel">
      <div className="panel-heading"><div><span className="eyebrow">product concentration</span><h3>Two product families hold nearly all exposure.</h3></div><EvidenceTag type="DERIVED" /></div>
      <div className="product-list">
        {products.map((product) => (
          <div className="product-row" key={product.id}>
            <div className="product-title"><b>{product.name}</b><span>{product.sample} shock shipments</span></div>
            <div className="product-bar"><i style={{ width: barWidth(product.exposureSharePct) }} /></div>
            <div className="product-value"><b>{formatMoney(product.positiveSensitivity)}</b><span>{formatPercent(product.cumulativeSharePct, 1)} cumulative</span></div>
          </div>
        ))}
      </div>
      <div className="product-note"><span>Crude Oil + Refined Petrochemicals</span><b>{formatPercent(products[1]?.cumulativeSharePct, 1)} of positive sensitivity</b></div>
    </article>
  )
}

function ServiceTablePanel() {
  return (
    <article className="panel service-panel">
      <div className="panel-heading"><div><span className="eyebrow">route / service evidence</span><h3>Observed operating state, with Held kept open.</h3></div><EvidenceTag type="FACT" /></div>
      <div className="service-table-wrap"><table className="service-table"><thead><tr><th>route / status</th><th>universe</th><th>sample / tonnes</th><th>DIFOT / 90% interval</th><th>cost / t</th><th>positive exposure</th><th>delay / age</th></tr></thead><tbody>
        {routes.map((route) => <tr key={route.id}><td><b>{routeLabel(route.routeOrStatus)}</b></td><td><span className={`universe-label ${route.universe}`}>{universeLabel(route.universe)}</span></td><td>{route.sample} · {formatNumber(route.tonnes, 1)}t</td><td>{route.difot == null ? <span className="open-value">open · no completed outcome</span> : `${formatPercent(route.difot)} · ${route.difotHits}/${route.difotDenominator} · ${formatPercent(route.serviceInterval?.lower)}–${formatPercent(route.serviceInterval?.upper)}`}</td><td>{formatPerTon(route.costPerTon)}</td><td>{route.positiveSensitivity == null ? 'benchmark' : formatMoney(route.positiveSensitivity)}</td><td>{route.universe === 'held_open' ? `${formatNumber(route.heldAgeDays, 1)}d age` : `${formatNumber(route.deliveredDelayDays, 1)}d total`}</td></tr>)}
      </tbody></table></div>
      <p className="panel-note">Direct is a historical benchmark. Emergency-mode contribution percentages, where shown in the cell explorer, are judged against fixed contracted revenue and are not a standalone route verdict.</p>
    </article>
  )
}

function RouteEvidencePanel() {
  return (
    <article className="panel route-evidence-panel">
      <div className="panel-heading"><div><span className="eyebrow">product-matched route evidence</span><h3>Observed candidates are pilots, not rollout approvals.</h3></div><StatusPill tone="open">gates missing</StatusPill></div>
      <div className="route-evidence-grid">
        {routeEvidence.map((row) => (
          <div className="route-card" key={row.id}>
            <div className="route-card-top"><b>{row.product}</b><span className={`evidence-status ${row.status}`}>{titleCase(row.status)}</span></div>
            <div className="route-compare"><div><small>candidate route</small><strong>{routeLabel(row.candidateRoute)}</strong><span>{formatPerTon(row.candidate.costPerTon)} / t · {formatPercent(row.candidate.difot)} DIFOT</span></div><div className="versus">vs</div><div><small>comparison route</small><strong>{row.comparisonRoute ? routeLabel(row.comparisonRoute) : 'not observed'}</strong><span>{row.comparison ? `${formatPerTon(row.comparison.costPerTon)} / t · ${formatPercent(row.comparison.difot)} DIFOT` : 'n.a.'}</span></div></div>
            <div className="route-card-foot"><span>{row.candidate.sample} vs {row.comparison?.sample ?? 'n.a.'} observed shipments</span><span>{row.approvalGates.length} missing gates</span></div>
          </div>
        ))}
      </div>
      <p className="panel-note">Each comparison is product-matched and observational. Capacity, live all-in quote, cargo feasibility, insurance and approved service requirements remain open.</p>
    </article>
  )
}

function HeldLedgerPanel() {
  const summary = heldLedger.summary
  return (
    <article className="panel held-panel">
      <div className="panel-heading"><div><span className="eyebrow">held-open triage</span><h3>Held is an open ledger, not a release schedule.</h3></div><StatusPill tone="open">{summary.shipments} open shipments</StatusPill></div>
      <div className="held-summary"><div><small>contracted / unrecognized</small><b>{formatMoney(summary.contractedRevenue)}</b></div><div><small>accrued total cost</small><b>{formatMoney(summary.accruedCost)}</b></div><div><small>full-life gap</small><b className="negative-text">{formatMoney(summary.fullLifeGap)}</b></div><div><small>age cumulative / median / p90</small><b>{formatNumber(summary.cumulativeAgeDays)}d / {formatNumber(summary.medianAgeDays, 1)}d / {formatNumber(summary.p90AgeDays, 1)}d</b></div></div>
      <div className="held-table-wrap"><table className="held-table"><thead><tr><th>shipment / customer</th><th>product</th><th>age</th><th>revenue unlock</th><th>accrued cost</th><th>optimistic ceiling / t</th><th>forward contribution</th></tr></thead><tbody>
        {heldLedger.rows.map((row) => <tr key={row.shipmentId}><td><b>{row.shipmentId}</b><small>{row.customer}</small></td><td>{row.product}</td><td><span className="age-tag">{formatNumber(row.heldAgeDays, 1)}d</span></td><td className="money-cell">{formatMoney(row.revenueUnlocked, 2)}</td><td className="money-cell">{formatMoney(row.accruedCost, 2)}</td><td>{formatPerTon(row.optimisticCeilingPerTon)}</td><td><span className="open-value">open</span></td></tr>)}
      </tbody></table></div>
      <p className="panel-note">Forward contribution stays <b>null</b> until approved surcharge, incremental cost, future unavoidable cost, feasibility, capacity, insurance and service inputs are present. The per-shipment optimistic ceiling assumes accrued cost is sunk and future penalty/surcharge are zero.</p>
    </article>
  )
}

function CellDetail({ cell }) {
  if (!cell) return <div className="cell-detail empty">Select a decision cell to inspect its evidence and gates.</div>
  return (
    <aside className="cell-detail">
      <div className="detail-heading"><div><span className="eyebrow">selected decision cell</span><h3>{cell.customer}</h3><p>{cell.product} · {routeLabel(cell.routeOrStatus)}</p></div><StatusPill tone={cell.decisionStatus === 'blocked_missing_input' ? 'open' : 'accepted'}>{titleCase(cell.decisionStatus)}</StatusPill></div>
      <div className="detail-facts"><div><small>historical contribution</small><b className={cell.historicalContribution < 0 ? 'negative-text' : 'positive'}>{formatMoney(cell.historicalContribution)}</b></div><div><small>positive sensitivity</small><b>{formatMoney(cell.positiveSensitivity)}</b></div><div><small>DIFOT / sample</small><b>{cell.difot == null ? 'open' : `${formatPercent(cell.difot)} · ${cell.difotHits}/${cell.difotDenominator}`}</b></div><div><small>{cell.universe === 'held_open' ? 'Held age / revenue' : 'surcharges'} </small><b>{cell.universe === 'held_open' ? `${formatNumber(cell.heldAgeDays, 1)}d · ${formatMoney(cell.heldRevenue)}` : `${formatMoney(cell.zeroMarginSurcharge)} / ${formatMoney(cell.benchmarkPreservingSurcharge)}`}</b></div></div>
      <div className="detail-columns"><div><h4>Business problem</h4><div className="chip-list">{cell.businessProblems.map((problem) => <span className="problem-chip" key={problem}>{titleCase(problem)}</span>)}</div><h4>Recommended posture</h4><div className="chip-list">{cell.recommendedPostures.map((posture) => <span className="posture-chip" key={posture}>{titleCase(posture)}</span>)}</div>{cell.operationalOptions.length > 0 && <><h4>Observed operational option</h4><div className="chip-list"><span className="option-chip">{titleCase(cell.operationalOptions[0])}</span></div></>}</div><div><h4>Missing approval inputs</h4><div className="gate-list">{cell.approvalGateDetails.map((gate) => <div key={gate.name}><span>{gate.name}</span><small>{gate.ownerRole}</small></div>)}</div></div></div>
      <div className="release-box"><small>owner · {cell.ownerRole}</small><b>Release condition</b><span>{cell.releaseCondition}</span></div>
    </aside>
  )
}

function DecisionExplorer() {
  const [customerFilter, setCustomerFilter] = useState('all')
  const [universeFilter, setUniverseFilter] = useState('all')
  const [selectedId, setSelectedId] = useState(decisionCells[0]?.id ?? '')
  const filtered = useMemo(() => decisionCells.filter((cell) => (customerFilter === 'all' || cell.customer === customerFilter) && (universeFilter === 'all' || cell.universe === universeFilter)), [customerFilter, universeFilter])
  const selected = decisionCells.find((cell) => cell.id === selectedId) ?? filtered[0]
  return (
    <div className="decision-layout">
      <article className="panel decision-panel">
        <div className="panel-heading"><div><span className="eyebrow">{decisionCells.length} observed decision cells</span><h3>From aggregate exposure to an accountable posture.</h3></div><div className="cell-filters"><label>customer<select aria-label="Filter cells by customer" value={customerFilter} onChange={(event) => setCustomerFilter(event.target.value)}><option value="all">All customers</option>{customers.map((customer) => <option key={customer.name} value={customer.name}>{customer.name}</option>)}</select></label><label>universe<select aria-label="Filter cells by universe" value={universeFilter} onChange={(event) => setUniverseFilter(event.target.value)}><option value="all">All universes</option><option value="post_blockade_delivered">Delivered</option><option value="held_open">Held open</option></select></label></div></div>
        <div className="cell-table-wrap"><table className="cell-table"><thead><tr><th>customer / product</th><th>route / status</th><th>n</th><th>contribution</th><th>positive sensitivity</th><th>DIFOT / Held</th><th>posture</th></tr></thead><tbody>
          {filtered.map((cell) => <tr className={selected?.id === cell.id ? 'selected' : ''} key={cell.id} onClick={() => setSelectedId(cell.id)}><td><b>{cell.customer}</b><small>{cell.product}</small></td><td><span className={`universe-label ${cell.universe}`}>{routeLabel(cell.routeOrStatus)}</span></td><td>{cell.sample}</td><td className={cell.historicalContribution < 0 ? 'negative-text' : ''}>{formatMoney(cell.historicalContribution)}</td><td>{formatMoney(cell.positiveSensitivity)}</td><td>{cell.difot == null ? <span className="open-value">{formatNumber(cell.heldAgeDays, 1)}d age</span> : `${formatPercent(cell.difot)} · ${cell.difotHits}/${cell.difotDenominator}`}</td><td><span className="table-posture">{titleCase(cell.recommendedPostures[0])}</span></td></tr>)}
        </tbody></table></div>
        <p className="panel-note">Filters only change the displayed subset. Source totals and reconciliations remain generated from all {metadata.sourceRows} accepted records.</p>
      </article>
      <CellDetail cell={selected} />
    </div>
  )
}

function DecisionRegisterPanel() {
  return (
    <article className="panel register-panel">
      <div className="panel-heading"><div><span className="eyebrow">board-facing decision register</span><h3>Protect, change, pilot, review or freeze — with the gate beside it.</h3></div><EvidenceTag type="PROPOSAL" /></div>
      <div className="register-list">
        {decisionRegister.map((decision) => <details className="register-row" key={decision.decisionId}><summary><span className="decision-id">{decision.decisionId}</span><span className="register-scope"><b>{decision.scope.customer}</b><small>{decision.scope.product} · {routeLabel(decision.scope.routeOrStatus)}</small></span><span className="register-problem">{decision.businessProblem.map((problem) => <em key={problem}>{titleCase(problem)}</em>)}</span><span className="register-owner">{decision.ownerRole}</span><span className="chevron">+</span></summary><div className="register-detail"><div><small>posture</small><div className="chip-list">{decision.posture.map((posture) => <span className="posture-chip" key={posture}>{titleCase(posture)}</span>)}</div></div><div><small>activation evidence</small><p>{decision.activationEvidence.map(titleCase).join(' · ') || 'Historical review only.'}</p></div><div><small>missing approval inputs</small><p>{decision.approvalGates.length ? decision.approvalGates.join(' · ') : 'None for this historical review.'}</p></div><div><small>release condition</small><p>{decision.releaseCondition}</p></div></div></details>)}
      </div>
      <p className="panel-note">The register never generates a permanent exit recommendation. New commitments can be frozen pending approved prospective economics; execution remains owner-gated.</p>
    </article>
  )
}

function MethodologyPanel() {
  const gateCount = methodology.approvalGates.length
  return (
    <div className="methodology-grid">
      <article className="panel methodology-panel">
        <div className="panel-heading"><div><span className="eyebrow">methodology / evidence language</span><h3>Every claim carries its epistemic label.</h3></div><StatusPill tone="accepted">source accepted</StatusPill></div>
        <div className="evidence-list">{Object.entries(methodology.evidenceLabels).map(([type, description]) => <div key={type}><EvidenceTag type={type} /><p>{description}</p></div>)}</div>
        <div className="source-line"><b>{metadata.sourceFile}</b><span>{metadata.sourceRows} rows · {metadata.uniqueShipmentIds} unique Shipment_IDs</span><span>{dateLabel(metadata.observationStart)} — {dateLabel(metadata.observationEnd)}</span></div>
      </article>
      <article className="panel gate-panel">
        <div className="panel-heading"><div><span className="eyebrow">execution boundary</span><h3>{gateCount} approval gates remain open.</h3></div><StatusPill tone="open">MISSING_INPUT</StatusPill></div>
        <div className="gate-catalog">{methodology.approvalGates.map((gate) => <div key={gate.name}><b>{gate.name}</b><span>{gate.ownerRole}</span><small>{gate.requiredFor}</small></div>)}</div>
        <p className="panel-note">No freight quote, route-week capacity, insurance term, clearance rate, recovery rate or service threshold is inferred from the workbook.</p>
      </article>
    </div>
  )
}

function AppendixPanel() {
  const diagnostic = appendixDiagnostics.compositeScore
  return (
    <article className="panel appendix-panel">
      <div className="panel-heading"><div><span className="eyebrow">appendix diagnostic</span><h3>Composite score: visible, isolated, non-decisive.</h3></div><StatusPill tone="neutral">decision use: false</StatusPill></div>
      <div className="appendix-warning">{diagnostic.warning}</div>
      <div className="appendix-body"><div><small>policy weights</small><div className="weight-line">M {formatPercent(diagnostic.weights.M * 100, 0)} · I {formatPercent(diagnostic.weights.I * 100, 0)} · D {formatPercent(diagnostic.weights.D * 100, 0)} · C {formatPercent(diagnostic.weights.C * 100, 0)}</div></div><div><small>primary priority basis</small><div className="weight-line">positive exposure dollars · historical contribution · Held revenue · hard evidence flags</div></div></div>
      <div className="appendix-table-wrap"><table className="appendix-table"><thead><tr><th>diagnostic rank</th><th>member</th><th>score</th><th>positive sensitivity</th><th>M</th><th>I</th><th>D</th><th>C</th></tr></thead><tbody>{diagnostic.rows.customers.slice(0, 5).map((row, index) => <tr key={row.id}><td>{String(index + 1).padStart(2, '0')}</td><td>{row.name}</td><td>{Number(row.compositeScore).toFixed(1)}</td><td>{formatMoney(row.positiveSensitivity)}</td><td>{formatPercent(row.M, 0)}</td><td>{formatPercent(row.I, 0)}</td><td>{formatPercent(row.D, 0)}</td><td>{formatPercent(row.C, 0)}</td></tr>)}</tbody></table></div>
    </article>
  )
}

function App() {
  const [selectedCustomer, setSelectedCustomer] = useState('')
  const selectedExposure = customers.find((customer) => customer.name === selectedCustomer)
  const deliveredService = serviceEvidence.post_blockade_delivered
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">S</span><div><b>STRAIT OUTTA</b><strong>HORMUZ</strong></div></div>
        <div className="sidebar-kicker"><i /> historical evidence engine</div>
        <nav aria-label="Dashboard sections">
          <a className="active" href="#command">Command</a><a href="#bridge">Financial bridge</a><a href="#exposure">Exposure</a><a href="#held">Held ledger <span>{heldLedger.summary.shipments}</span></a><a href="#decisions">Decision cells</a><a href="#register">Register</a><a href="#methodology">Methodology</a>
        </nav>
        <div className="sidebar-bottom"><div className="source-block"><small>accepted source</small><b>{metadata.sourceRows} shipments</b><span>{metadata.uniqueShipmentIds} unique IDs</span><span>{metadata.sourceStatus}</span></div><div className="sidebar-foot"><span>R2 / INTERNAL</span><span>{dateLabel(metadata.observationEnd)}</span></div></div>
      </aside>
      <main className="main-content">
        <header className="topbar"><div className="breadcrumb">R2 <i>/</i> analytical engine</div><div className="topbar-meta"><span><i /> generated {dateLabel(metadata.generatedAt.slice(0, 10))}</span><span>schema {dashboardData.schemaVersion}</span></div></header>
        <div className="accepted-banner"><div><StatusPill tone="accepted">source accepted</StatusPill><span>{metadata.sourceRows} nonblank, unique Shipment_IDs · Python-generated output</span></div><span className="banner-note">No forward forecast or capacity model</span></div>
        <section className="hero" id="command"><div className="hero-copy"><span className="eyebrow">operational → commercial → strategic</span><h1>What moved,<br /><em>what broke.</em></h1><p>The accepted shipment ledger shows where route-cost exposure became a business problem, which cells need protection or change, and what management still has to approve before acting.</p><div className="hero-actions"><a className="primary-action" href="#register">Open decision register <span>↗</span></a><a className="quiet-action" href="#methodology">Read evidence rules</a></div></div><div className="hero-proof"><div className="proof-line" /><div className="proof-step"><span>01</span><b>Operational change</b><small>Direct benchmark → observed post-blockade routes</small></div><div className="proof-step"><span>02</span><b>Commercial consequence</b><small>{formatMoney(financialBridge.observedDeliveredContribution)} delivered contribution</small></div><div className="proof-step"><span>03</span><b>Strategic posture</b><small>protect · change · pilot · review · freeze</small></div></div></section>
        <section className="metric-grid" aria-label="Executive evidence"><Metric label="Accepted source" value={formatNumber(metadata.sourceRows)} detail={`${metadata.uniqueShipmentIds} unique Shipment_IDs · ${dateLabel(metadata.observationStart)} to ${dateLabel(metadata.observationEnd)}`} tone="blue" /><Metric label="Benchmark contribution" value={`+${formatMoney(financialBridge.benchmarkContribution)}`} detail="Direct-equivalent economics · delivered population" tone="positive" /><Metric label="Observed delivered contribution" value={formatMoney(financialBridge.observedDeliveredContribution)} detail={`${portfolio.postBlockadeDelivered.shipments} completed post-blockade shipments`} tone="negative" /><Metric label="Post-blockade DIFOT" value={formatPercent(deliveredService.difot)} detail={`${deliveredService.difotHits}/${deliveredService.difotDenominator} hits · 90% Jeffreys interval ${formatPercent(deliveredService.serviceInterval.lower)}–${formatPercent(deliveredService.serviceInterval.upper)}`} tone="amber" /></section>
        <section className="section" id="bridge"><SectionHeading index="01 / financial through-line" title="The historical bridge is the board’s starting point." copy="Direct is a separate product-matched reference. Delivered contribution and Held exposure are not blended." /><div className="two-column"><BridgePanel /><UniversePanel /></div></section>
        <section className="section" id="exposure"><SectionHeading index="02 / concentration" title="Put dollar exposure ahead of a composite score." copy={selectedExposure ? `Focus: ${selectedExposure.name}. The selection changes attention, not the generated source totals.` : 'The largest customer and product exposures define where a board conversation should begin.'} /><div className="two-column exposure-columns"><ExposurePanel selectedCustomer={selectedCustomer} setSelectedCustomer={setSelectedCustomer} /><ProductPanel /></div></section>
        <section className="section"><SectionHeading index="03 / route evidence" title="Compare like cargo before changing the lane." copy="A lower observed cost and higher observed DIFOT can justify a controlled pilot hypothesis. It cannot prove causality, capacity or rollout readiness." /><ServiceTablePanel /><div className="route-evidence-spacer" /><RouteEvidencePanel /></section>
        <section className="section" id="held"><SectionHeading index="04 / Held triage" title="The open queue carries revenue, cost and age — not a release plan." copy="Held shipments have no completed service outcome. Their historical boundary is shown by shipment and cell; forward contribution remains open." /><HeldLedgerPanel /></section>
        <section className="section" id="decisions"><SectionHeading index="05 / decision grain" title="Every observed cell gets a problem, posture and gate." copy="Select a customer × product × route/status cell to see historical facts, derived problems, proposed posture and missing approval inputs." /><DecisionExplorer /></section>
        <section className="section" id="register"><SectionHeading index="06 / board register" title="Execution stays conditional until the evidence is approved." copy="The register separates commercial recovery from route pilots, insurance review and new-commitment freezes." /><DecisionRegisterPanel /></section>
        <section className="section" id="methodology"><SectionHeading index="07 / methodology" title="The engine is designed to be defended line by line." copy="Python is the analytical source of truth. React formats, filters and presents the generated schema." /><MethodologyPanel /></section>
        <section className="section"><SectionHeading index="08 / appendix" title="Keep the diagnostic where it belongs." copy="The composite is retained for transparency only; it never selects customers, products, routes or actions." /><AppendixPanel /></section>
        <footer className="app-footer"><span>STRAIT OUTTA HORMUZ / R2</span><span>{metadata.sourceRows} accepted records · schema {dashboardData.schemaVersion}</span><span>historical evidence · conditional execution</span></footer>
      </main>
    </div>
  )
}

export default App
