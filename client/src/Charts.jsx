import { VisAxis } from '@unovis/react/components/axis'
import { VisGroupedBar, VisGroupedBarSelectors } from '@unovis/react/components/grouped-bar'
import { VisLine } from '@unovis/react/components/line'
import { VisPlotline } from '@unovis/react/components/plotline'
import { VisScatter, VisScatterSelectors } from '@unovis/react/components/scatter'
import { VisTooltip } from '@unovis/react/components/tooltip'
import { VisXYContainer } from '@unovis/react/containers/xy-container'

const money = (value, digits = 1) => `$${(Number(value) / 1000000).toFixed(digits)}M`
const percent = (value, digits = 1) => `${Number(value).toFixed(digits)}%`
const shortName = (value) => value.split(' ')[0]

function ParetoChart({ data, activeCustomer, setActiveCustomer }) {
  return (
    <VisXYContainer
      ariaLabel="Customer positive sensitivity share and cumulative exposure"
      className="unovis-chart"
      data={data}
      height={270}
      margin={{ top: 18, right: 24, bottom: 48, left: 58 }}
      xDomain={[-0.5, data.length - 0.5]}
      yDomain={[0, 100]}
    >
      <VisGroupedBar
        barMinHeight={2}
        color={(customer) => customer.name === activeCustomer ? '#cc2e39' : '#1a211e'}
        dataStep={1}
        groupPadding={0.2}
        roundedCorners={false}
        x={(customer) => customer.rank}
        y={(customer) => customer.share}
        events={{
          [VisGroupedBarSelectors.bar]: {
            click: (customer) => setActiveCustomer(customer.name === activeCustomer ? '' : customer.name),
          },
        }}
      />
      <VisLine
        color="#cc2e39"
        curveType="linear"
        lineWidth={2}
        x={(customer) => customer.rank}
        y={(customer) => customer.cumulativeShare}
      />
      <VisPlotline
        axis="y"
        color="#cc2e39"
        labelColor="#cc2e39"
        labelPosition="top-right"
        labelSize={9}
        labelText="90% cutoff"
        lineStyle={[4, 4]}
        lineWidth={1}
        value={90}
      />
      <VisAxis
        domainLine={false}
        gridLine
        label="share of positive sensitivity"
        labelColor="#606562"
        labelFontSize="10px"
        tickFormat={(tick) => `${Number(tick).toFixed(0)}%`}
        tickTextColor="#606562"
        tickTextFontSize="10px"
        type="y"
      />
      <VisAxis
        domainLine={false}
        gridLine={false}
        tickFormat={(tick) => shortName(data[Math.round(Number(tick))]?.name ?? '')}
        tickTextColor="#606562"
        tickTextFontSize="10px"
        tickValues={data.map((customer) => customer.rank)}
        type="x"
      />
      <VisTooltip
        className="unovis-tooltip"
        triggers={{
          [VisGroupedBarSelectors.bar]: (customer) => `<strong>${customer.name}</strong><span>${money(customer.adverse)} positive sensitivity</span><span>${percent(customer.share)} of shock · ${percent(customer.cumulativeShare)} cumulative</span>`,
        }}
      />
    </VisXYContainer>
  )
}

function VulnerabilityChart({ data, activeCustomer, setActiveCustomer, max }) {
  return (
    <VisXYContainer
      ariaLabel="Customer impact versus rate severity map"
      className="unovis-chart"
      data={data}
      height={280}
      margin={{ top: 22, right: 20, bottom: 42, left: 72 }}
      xDomain={[0, 400]}
      yDomain={[0, max * 1.15]}
    >
      <VisScatter
        color={(customer) => customer.name === activeCustomer ? '#cc2e39' : '#1a211e'}
        events={{
          [VisScatterSelectors.point]: {
            click: (customer) => setActiveCustomer(customer.name === activeCustomer ? '' : customer.name),
          },
        }}
        label={(customer) => shortName(customer.name)}
        labelColor="#606562"
        labelHideOverlapping={false}
        labelPosition="top"
        shape="circle"
        size={(customer) => customer.contracted}
        sizeRange={[12, 36]}
        strokeColor={(customer) => customer.name === activeCustomer ? '#cc2e39' : '#1a211e'}
        strokeWidth={1}
        x={(customer) => customer.severity}
        y={(customer) => customer.adverse}
      />
      <VisAxis
        domainLine={false}
        gridLine={false}
        label="rate severity"
        labelColor="#606562"
        labelFontSize="10px"
        tickFormat={(tick) => `${Number(tick).toFixed(0)}%`}
        tickTextColor="#606562"
        tickTextFontSize="10px"
        type="x"
      />
      <VisAxis
        domainLine={false}
        gridLine
        label="positive adverse $"
        labelColor="#606562"
        labelFontSize="10px"
        tickFormat={(tick) => money(tick, 0)}
        tickTextColor="#606562"
        tickTextFontSize="10px"
        type="y"
      />
      <VisTooltip
        className="unovis-tooltip"
        triggers={{
          [VisScatterSelectors.point]: (customer) => `<strong>${customer.name}</strong><span>${money(customer.adverse)} positive sensitivity</span><span>${percent(customer.severity)} severity · ${money(customer.contracted)} contracted</span>`,
        }}
      />
    </VisXYContainer>
  )
}

export default function Charts({ kind, ...props }) {
  return kind === 'pareto' ? <ParetoChart {...props} /> : <VulnerabilityChart {...props} />
}
