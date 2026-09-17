import { useEffect, useMemo, useState } from 'react'
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
  if (value == null) return 'n.a.'
  const sign = Number(value) < 0 ? '−' : ''
  return `${sign}$${(Math.abs(Number(value)) / 1000000).toFixed(digits)}M`
}

const formatUsd = (value) => {
  if (value == null) return 'n.a.'
  const amount = Math.abs(Number(value))
  const sign = Number(value) < 0 ? '−' : ''
  if (amount >= 1000000) return `${sign}$${(amount / 1000000).toFixed(2)}M`
  if (amount >= 1000) return `${sign}$${(amount / 1000).toFixed(1)}k`
  return `${sign}$${amount.toFixed(0)}`
}

const formatPercent = (value, digits = 1) => (value == null ? 'n.a.' : `${Number(value).toFixed(digits)}%`)
const formatPerTon = (value) => (value == null ? 'n.a.' : `$${Number(value).toFixed(2)}`)
const formatNumber = (value, digits = 0) => (value == null ? 'n.a.' : Number(value).toLocaleString('en-US', { maximumFractionDigits: digits }))
const dateLabel = (value) => new Date(`${value}T00:00:00Z`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
const titleCase = (value) => value.replaceAll('_', ' ')
const problemLabel = (value) => ({ delivery_outcome_open: 'Delivery outcome pending' })[value] ?? titleCase(value)
const routeLabel = (value) => value === 'Direct (Pre-Blockade)' ? 'Direct / benchmark' : value
const universeLabel = (value) => ({ direct_reference: 'Direct reference', post_blockade_delivered: 'Delivered', held_open: 'Held' })[value] ?? value
const decisionStatusLabel = (value) => ({ blocked_missing_input: 'Approval required', approval_required: 'Approval required', conditional: 'Conditional', actionable_historical: 'Historical action' })[value] ?? titleCase(value)
const evidenceLabel = (value) => value === 'MISSING_INPUT' ? 'INPUT_REQUIRED' : value
const barWidth = (value) => `${Math.max(0, Math.min(100, Number(value) || 0))}%`

function EvidenceTag({ type }) {
  return <span className={`evidence-tag ${String(type).toLowerCase()}`}>{type}</span>
}

function StatusPill({ children, tone = 'neutral' }) {
  return <span className={`status-pill ${tone}`}><i />{children}</span>
}

function DetailModal({ eyebrow, title, subtitle, onClose, children }) {
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div className="detail-modal" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <div><span className="eyebrow">{eyebrow}</span><h3>{title}</h3><p>{subtitle}</p></div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close analysis">×</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}

function SectionHeading({ title, copy, action }) {
  return (
    <div className="section-heading">
      <div>
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
        <div><span className="eyebrow">analytical universes</span><h3>Three evidence universes.</h3></div>
        <StatusPill tone="accepted">{portfolio.shipments} records</StatusPill>
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
      <div className="panel-heading"><div><span className="eyebrow">route / service evidence</span><h3>Observed routes and service.</h3></div><EvidenceTag type="FACT" /></div>
      <div className="service-table-wrap"><table className="service-table"><thead><tr><th>route / status</th><th>universe</th><th>sample / tonnes</th><th>DIFOT / 90% interval</th><th>cost / t</th><th>positive exposure</th><th>delay / age</th></tr></thead><tbody>
        {routes.map((route) => <tr key={route.id}><td><b>{routeLabel(route.routeOrStatus)}</b></td><td><span className={`universe-label ${route.universe}`}>{universeLabel(route.universe)}</span></td><td>{route.sample} · {formatNumber(route.tonnes, 1)}t</td><td>{route.difot == null ? <span className="na-value">n.a. · no completed outcome</span> : `${formatPercent(route.difot)} · ${route.difotHits}/${route.difotDenominator} · ${formatPercent(route.serviceInterval?.lower)}-${formatPercent(route.serviceInterval?.upper)}`}</td><td>{formatPerTon(route.costPerTon)}</td><td>{route.positiveSensitivity == null ? 'benchmark' : formatMoney(route.positiveSensitivity)}</td><td>{route.universe === 'held_open' ? `${formatNumber(route.heldAgeDays, 1)}d age` : `${formatNumber(route.deliveredDelayDays, 1)}d total`}</td></tr>)}
      </tbody></table></div>
      <p className="panel-note">Direct is the historical benchmark. Route comparisons are observational, not rollout approvals.</p>
    </article>
  )
}

function RouteEvidencePanel() {
  return (
    <article className="panel route-evidence-panel">
      <div className="panel-heading"><div><span className="eyebrow">product-matched route evidence</span><h3>Observed candidates for controlled pilots.</h3></div><StatusPill tone="required">approval required</StatusPill></div>
      <div className="route-evidence-grid">
        {routeEvidence.map((row) => (
          <div className="route-card" key={row.id}>
            <div className="route-card-top"><b>{row.product}</b><span className={`evidence-status ${row.status}`}>{titleCase(row.status)}</span></div>
            <div className="route-compare"><div><small>candidate route</small><strong>{routeLabel(row.candidateRoute)}</strong><span>{formatPerTon(row.candidate.costPerTon)} / t · {formatPercent(row.candidate.difot)} DIFOT</span></div><div className="versus">vs</div><div><small>comparison route</small><strong>{row.comparisonRoute ? routeLabel(row.comparisonRoute) : 'not observed'}</strong><span>{row.comparison ? `${formatPerTon(row.comparison.costPerTon)} / t · ${formatPercent(row.comparison.difot)} DIFOT` : 'n.a.'}</span></div></div>
            <div className="route-card-foot"><span>{row.candidate.sample} vs {row.comparison?.sample ?? 'n.a.'} observed shipments</span><span>{row.approvalGates.length} gates</span></div>
          </div>
        ))}
      </div>
      <p className="panel-note">Each comparison is product-matched and observational. Pilot approval uses the listed owner gates.</p>
    </article>
  )
}

function HeldLedgerPanel() {
  const summary = heldLedger.summary
  const [selectedShipment, setSelectedShipment] = useState(null)
  return (
    <article className="panel held-panel">
      <div className="panel-heading"><div><span className="eyebrow">held ledger</span><h3>Revenue, cost and age by shipment.</h3></div><StatusPill tone="neutral">{summary.shipments} held shipments</StatusPill></div>
      <div className="held-summary"><div><small>contracted / unrecognized</small><b>{formatMoney(summary.contractedRevenue)}</b></div><div><small>accrued total cost</small><b>{formatMoney(summary.accruedCost)}</b></div><div><small>full-life gap</small><b className="negative-text">{formatMoney(summary.fullLifeGap)}</b></div><div><small>age cumulative / median / p90</small><b>{formatNumber(summary.cumulativeAgeDays)}d / {formatNumber(summary.medianAgeDays, 1)}d / {formatNumber(summary.p90AgeDays, 1)}d</b></div></div>
      <div className="held-card-grid">
        {heldLedger.rows.map((row) => (
          <button type="button" className="shipment-card" key={row.shipmentId} onClick={() => setSelectedShipment(row)}>
            <div className="card-topline"><span className="card-code">{row.shipmentId}</span><span className="age-tag">{formatNumber(row.heldAgeDays, 1)}d</span></div>
            <strong className="card-title">{row.customer}</strong>
            <span className="card-subtitle">{row.product} · {routeLabel(row.routeOrStatus)}</span>
            <div className="card-metrics"><div><small>revenue</small><b>{formatUsd(row.revenueUnlocked)}</b></div><div><small>accrued cost</small><b>{formatUsd(row.accruedCost)}</b></div><div><small>ceiling / t</small><b>{formatPerTon(row.optimisticCeilingPerTon)}</b></div></div>
            <span className="card-action">Open analysis <span aria-hidden="true">↗</span></span>
          </button>
        ))}
      </div>
      <p className="panel-note">Forward contribution is not calculated for Held rows. The per-shipment ceiling assumes accrued cost is sunk and future penalty/surcharge are zero.</p>
      {selectedShipment && <DetailModal eyebrow="held shipment analysis" title={selectedShipment.shipmentId} subtitle={`${selectedShipment.customer} · ${selectedShipment.product}`} onClose={() => setSelectedShipment(null)}>
        <div className="modal-stat-grid"><div><small>route / status</small><strong>{routeLabel(selectedShipment.routeOrStatus)}</strong></div><div><small>cargo</small><strong>{formatNumber(selectedShipment.tonnes, 1)}t</strong></div><div><small>held age</small><strong>{formatNumber(selectedShipment.heldAgeDays, 1)}d</strong></div><div><small>evidence</small><strong>Historical fact</strong></div></div>
        <div className="modal-section"><span className="modal-label">financial position</span><div className="modal-stat-grid"><div><small>contracted revenue</small><strong>{formatUsd(selectedShipment.contractedRevenue)}</strong></div><div><small>accrued cost</small><strong>{formatUsd(selectedShipment.accruedCost)}</strong></div><div><small>current margin</small><strong className={selectedShipment.currentMargin < 0 ? 'negative-text' : ''}>{formatUsd(selectedShipment.currentMargin)}</strong></div><div><small>full-life gap</small><strong className={selectedShipment.fullLifeGap > 0 ? 'negative-text' : ''}>{formatUsd(selectedShipment.fullLifeGap)}</strong></div></div></div>
        <div className="modal-section"><span className="modal-label">cost and service signals</span><div className="modal-stat-grid"><div><small>insurance</small><strong>{formatUsd(selectedShipment.insuranceComponent)}</strong></div><div><small>penalty</small><strong>{formatUsd(selectedShipment.penaltyComponent)}</strong></div><div><small>optimistic ceiling</small><strong>{formatUsd(selectedShipment.optimisticIncrementalCostCeiling)}</strong></div><div><small>DIFOT / transit</small><strong>n.a. / n.a.</strong></div></div></div>
        <div className="release-box"><small>forward contribution</small><b>n.a. for Held rows</b><span>The ledger keeps observed revenue, accrued cost and age separate from any execution outcome.</span></div>
      </DetailModal>}
    </article>
  )
}

function DecisionExplorer() {
  const [customerFilter, setCustomerFilter] = useState('all')
  const [universeFilter, setUniverseFilter] = useState('all')
  const [selectedDecision, setSelectedDecision] = useState(null)
  const decisionByCell = useMemo(() => new Map(decisionRegister.map((decision) => [decision.cellId, decision])), [])
  const filtered = useMemo(() => decisionCells.filter((cell) => (customerFilter === 'all' || cell.customer === customerFilter) && (universeFilter === 'all' || cell.universe === universeFilter)), [customerFilter, universeFilter])
  return (
    <article className="panel decision-panel">
      <div className="panel-heading"><div><span className="eyebrow">{decisionCells.length} observed decision cells</span><h3>Select a customer × product cell.</h3></div><div className="cell-filters"><label>customer<select aria-label="Filter cells by customer" value={customerFilter} onChange={(event) => setCustomerFilter(event.target.value)}><option value="all">All customers</option>{customers.map((customer) => <option key={customer.name} value={customer.name}>{customer.name}</option>)}</select></label><label>universe<select aria-label="Filter cells by universe" value={universeFilter} onChange={(event) => setUniverseFilter(event.target.value)}><option value="all">All universes</option><option value="post_blockade_delivered">Delivered</option><option value="held_open">Held</option></select></label></div></div>
      <div className="decision-cell-grid">
        {filtered.map((cell) => {
          const decision = decisionByCell.get(cell.id)
          return (
            <button type="button" className="decision-cell-card" key={cell.id} onClick={() => decision && setSelectedDecision(decision)}>
              <div className="card-topline"><span className="decision-id">{decision?.decisionId ?? 'CELL'}</span><StatusPill tone={decision?.decisionStatus === 'blocked_missing_input' ? 'required' : 'accepted'}>{decisionStatusLabel(decision?.decisionStatus ?? 'actionable_historical')}</StatusPill></div>
              <strong className="card-title">{cell.customer}</strong>
              <span className="card-subtitle">{cell.product} · {routeLabel(cell.routeOrStatus)}</span>
              <div className="card-metrics"><div><small>sample</small><b>{cell.sample}</b></div><div><small>contribution</small><b className={cell.historicalContribution < 0 ? 'negative-text' : ''}>{formatMoney(cell.historicalContribution)}</b></div><div><small>positive sensitivity</small><b>{formatMoney(cell.positiveSensitivity)}</b></div></div>
              <div className="decision-card-footer"><span>{cell.difot == null ? `${formatNumber(cell.heldAgeDays, 1)}d Held age` : `${formatPercent(cell.difot)} DIFOT`}</span><span>{titleCase(cell.recommendedPostures[0])}</span></div>
              <span className="card-action">Open analysis <span aria-hidden="true">↗</span></span>
            </button>
          )
        })}
      </div>
      <p className="panel-note">Filters only change the displayed subset. Source totals and reconciliations remain generated from all {metadata.sourceRows} accepted records.</p>
      {selectedDecision && <DecisionModal decision={selectedDecision} eyebrow="decision cell analysis" onClose={() => setSelectedDecision(null)} />}
    </article>
  )
}

function DecisionRegisterPanel() {
  const [selectedDecision, setSelectedDecision] = useState(null)
  return (
    <article className="panel register-panel">
      <div className="panel-heading"><div><span className="eyebrow">board-facing decision register</span><h3>One posture, owner and gate per cell.</h3></div><EvidenceTag type="PROPOSAL" /></div>
      <div className="register-grid">
        {decisionRegister.map((decision) => (
          <button type="button" className="register-card" key={decision.decisionId} onClick={() => setSelectedDecision(decision)}>
            <div className="card-topline"><span className="decision-id">{decision.decisionId}</span><StatusPill tone={decision.decisionStatus === 'blocked_missing_input' ? 'required' : 'accepted'}>{decisionStatusLabel(decision.decisionStatus)}</StatusPill></div>
            <strong className="card-title">{decision.scope.customer}</strong>
            <span className="card-subtitle">{decision.scope.product} · {routeLabel(decision.scope.routeOrStatus)}</span>
            <div className="card-metrics"><div><small>positive sensitivity</small><b>{formatMoney(decision.exposure.positiveSensitivity)}</b></div><div><small>owner</small><b>{decision.ownerRole}</b></div><div><small>gates</small><b>{decision.approvalGates.length}</b></div></div>
            <div className="card-chip-row">{decision.businessProblem.slice(0, 2).map((problem) => <span className="problem-chip" key={problem}>{problemLabel(problem)}</span>)}{decision.businessProblem.length > 2 && <span className="more-chip">+{decision.businessProblem.length - 2}</span>}</div>
            <span className="card-action">Open registration <span aria-hidden="true">↗</span></span>
          </button>
        ))}
      </div>
      <p className="panel-note">The register separates historical evidence from execution decisions. No permanent exit or rollout approval is generated.</p>
      {selectedDecision && <DecisionModal decision={selectedDecision} onClose={() => setSelectedDecision(null)} />}
    </article>
  )
}

function DecisionModal({ decision, eyebrow = `board registration · ${decision.decisionId}`, onClose }) {
  const cell = decisionCells.find((item) => item.id === decision.cellId)
  return (
    <DetailModal eyebrow={eyebrow} title={decision.scope.customer} subtitle={`${decision.scope.product} · ${routeLabel(decision.scope.routeOrStatus)}`} onClose={onClose}>
      <div className="modal-stat-grid"><div><small>positive sensitivity</small><strong>{formatMoney(decision.exposure.positiveSensitivity)}</strong></div><div><small>historical contribution</small><strong className={decision.exposure.historicalContribution < 0 ? 'negative-text' : ''}>{formatMoney(decision.exposure.historicalContribution)}</strong></div><div><small>owner</small><strong>{decision.ownerRole}</strong></div><div><small>horizon</small><strong>{decision.horizon.value}</strong></div></div>
      <div className="modal-columns"><div className="modal-section"><span className="modal-label">business problem</span><div className="chip-list">{decision.businessProblem.map((problem) => <span className="problem-chip" key={problem}>{problemLabel(problem)}</span>)}</div><span className="modal-label">recommended posture</span><div className="chip-list">{decision.posture.map((posture) => <span className="posture-chip" key={posture}>{titleCase(posture)}</span>)}</div><span className="modal-label">activation evidence</span><p className="modal-copy">{decision.activationEvidence.map(problemLabel).join(' · ') || 'Historical review only.'}</p></div><div className="modal-section"><span className="modal-label">approval gates</span><div className="modal-gate-list">{decision.approvalGateDetails.map((gate) => <div key={gate.name}><b>{gate.name}</b><small>{gate.ownerRole} · {gate.requiredFor}</small></div>)}</div></div></div>
      <div className="modal-stat-grid modal-secondary-stats"><div><small>DIFOT / sample</small><strong>{cell?.difot == null ? 'n.a.' : `${formatPercent(cell.difot)} · ${cell.difotHits}/${cell.difotDenominator}`}</strong></div><div><small>Held revenue</small><strong>{formatMoney(decision.exposure.heldRevenue)}</strong></div><div><small>decision status</small><strong>{decisionStatusLabel(decision.decisionStatus)}</strong></div><div><small>evidence</small><strong>Proposal</strong></div></div>
      <div className="release-box"><small>release condition</small><b>{decision.releaseCondition}</b><span>Owner: {decision.ownerRole}</span></div>
    </DetailModal>
  )
}

function MethodologyPanel() {
  const gateCount = methodology.approvalGates.length
  return (
    <div className="methodology-grid">
      <article className="panel methodology-panel">
        <div className="panel-heading"><div><span className="eyebrow">method / evidence language</span><h3>Every claim carries a label.</h3></div><StatusPill tone="accepted">source accepted</StatusPill></div>
        <div className="evidence-list">{Object.entries(methodology.evidenceLabels).map(([type, description]) => <div key={type}><EvidenceTag type={evidenceLabel(type)} /><p>{description}</p></div>)}</div>
        <div className="source-line"><b>{metadata.sourceFile}</b><span>{metadata.sourceRows} rows · {metadata.uniqueShipmentIds} unique Shipment_IDs</span><span>{dateLabel(metadata.observationStart)} - {dateLabel(metadata.observationEnd)}</span></div>
      </article>
      <article className="panel gate-panel">
        <div className="panel-heading"><div><span className="eyebrow">execution boundary</span><h3>{gateCount} owner approvals define execution.</h3></div><StatusPill tone="required">INPUT_REQUIRED</StatusPill></div>
        <div className="gate-catalog">{methodology.approvalGates.map((gate) => <div key={gate.name}><b>{gate.name}</b><span>{gate.ownerRole}</span><small>{gate.requiredFor}</small></div>)}</div>
        <p className="panel-note">Execution values are owner-entered; the historical engine does not derive them.</p>
      </article>
    </div>
  )
}

function AppendixPanel() {
  const diagnostic = appendixDiagnostics.compositeScore
  return (
    <details className="appendix-drawer">
      <summary><span>Appendix diagnostic</span><span>non-decisive</span></summary>
      <article className="panel appendix-panel">
        <div className="appendix-warning">{diagnostic.warning}</div>
        <div className="appendix-body"><div><small>policy weights</small><div className="weight-line">M {formatPercent(diagnostic.weights.M * 100, 0)} · I {formatPercent(diagnostic.weights.I * 100, 0)} · D {formatPercent(diagnostic.weights.D * 100, 0)} · C {formatPercent(diagnostic.weights.C * 100, 0)}</div></div><div><small>primary priority basis</small><div className="weight-line">positive exposure dollars · historical contribution · Held revenue · hard evidence flags</div></div></div>
        <div className="appendix-table-wrap"><table className="appendix-table"><thead><tr><th>diagnostic rank</th><th>member</th><th>score</th><th>positive sensitivity</th><th>M</th><th>I</th><th>D</th><th>C</th></tr></thead><tbody>{diagnostic.rows.customers.slice(0, 5).map((row, index) => <tr key={row.id}><td>{String(index + 1).padStart(2, '0')}</td><td>{row.name}</td><td>{Number(row.compositeScore).toFixed(1)}</td><td>{formatMoney(row.positiveSensitivity)}</td><td>{formatPercent(row.M, 0)}</td><td>{formatPercent(row.I, 0)}</td><td>{formatPercent(row.D, 0)}</td><td>{formatPercent(row.C, 0)}</td></tr>)}</tbody></table></div>
      </article>
    </details>
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
          <a className="active" href="#command">Command</a><a href="#bridge">Financial bridge</a><a href="#exposure">Exposure</a><a href="#held">Held ledger <span>{heldLedger.summary.shipments}</span></a><a href="#decisions">Decision cells</a><a href="#register">Register</a><a href="#methodology">Method</a>
        </nav>
        <div className="sidebar-bottom"><div className="source-block"><small>accepted source</small><b>{metadata.sourceRows} shipments</b><span>{metadata.uniqueShipmentIds} unique IDs</span><span>{metadata.sourceStatus}</span></div><div className="sidebar-foot"><span>R2 / INTERNAL</span><span>{dateLabel(metadata.observationEnd)}</span></div></div>
      </aside>
      <main className="main-content">
        <header className="topbar"><div className="breadcrumb">R2 <i>/</i> analytical engine</div><div className="topbar-meta"><span><i /> generated {dateLabel(metadata.generatedAt.slice(0, 10))}</span><span>schema {dashboardData.schemaVersion}</span></div></header>
        <div className="accepted-banner"><div><StatusPill tone="accepted">source accepted</StatusPill><span>{metadata.sourceRows} nonblank, unique Shipment_IDs · Python-generated output</span></div><span className="banner-note">Historical evidence · owner-gated execution</span></div>
        <section className="hero" id="command"><div className="hero-copy"><span className="eyebrow">Board review</span><h1>What moved. What broke.</h1><p>The shipment ledger links route-cost exposure to commercial posture, then carries each action to an owner gate.</p><div className="hero-actions"><a className="primary-action" href="#register">Open decision register <span>↗</span></a><a className="quiet-action" href="#methodology">Read method</a></div></div></section>
        <section className="metric-grid" aria-label="Executive evidence"><Metric label="Accepted source" value={formatNumber(metadata.sourceRows)} detail={`${metadata.uniqueShipmentIds} unique Shipment_IDs · ${dateLabel(metadata.observationStart)} to ${dateLabel(metadata.observationEnd)}`} tone="blue" /><Metric label="Benchmark contribution" value={`+${formatMoney(financialBridge.benchmarkContribution)}`} detail="Direct-equivalent economics · delivered population" tone="positive" /><Metric label="Observed delivered contribution" value={formatMoney(financialBridge.observedDeliveredContribution)} detail={`${portfolio.postBlockadeDelivered.shipments} completed post-blockade shipments`} tone="negative" /><Metric label="Post-blockade DIFOT" value={formatPercent(deliveredService.difot)} detail={`${deliveredService.difotHits}/${deliveredService.difotDenominator} hits · 90% Jeffreys interval ${formatPercent(deliveredService.serviceInterval.lower)}-${formatPercent(deliveredService.serviceInterval.upper)}`} tone="amber" /></section>
        <section className="section" id="bridge"><SectionHeading index="01 / financial bridge" title="Economics by evidence universe." /><div className="two-column"><BridgePanel /><UniversePanel /></div></section>
        <section className="section" id="exposure"><SectionHeading index="02 / concentration" title="Concentration before composite ranking." copy={selectedExposure ? `Focus: ${selectedExposure.name}.` : undefined} /><div className="two-column exposure-columns"><ExposurePanel selectedCustomer={selectedCustomer} setSelectedCustomer={setSelectedCustomer} /><ProductPanel /></div></section>
        <section className="section"><SectionHeading index="03 / route evidence" title="Product-matched routes and observed service." /><ServiceTablePanel /><div className="route-evidence-spacer" /><RouteEvidencePanel /></section>
        <section className="section" id="held"><SectionHeading index="04 / Held ledger" title="Revenue, cost and age by shipment." /><HeldLedgerPanel /></section>
        <section className="section" id="decisions"><SectionHeading index="05 / decision cells" title="One posture and gate per observed cell." /><DecisionExplorer /></section>
        <section className="section" id="register"><SectionHeading index="06 / board register" title="Board actions with owner gates." /><DecisionRegisterPanel /></section>
        <section className="section" id="methodology"><SectionHeading index="07 / method" title="Method, labels and owner gates." /><MethodologyPanel /><AppendixPanel /></section>
        <footer className="app-footer"><span>STRAIT OUTTA HORMUZ / R2</span><span>{metadata.sourceRows} accepted records · schema {dashboardData.schemaVersion}</span><span>historical evidence · conditional execution</span></footer>
      </main>
    </div>
  )
}

export default App
