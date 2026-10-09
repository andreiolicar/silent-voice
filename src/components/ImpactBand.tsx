import './impact-band.css'

const highlights = [
  { value: '3', label: 'Tecnologias integradas' },
  { value: '1', label: 'Dispositivo vestível' },
  { value: '1', label: 'App para conectar' },
  { value: '100%', label: 'Foco em autonomia' },
] as const

export function ImpactBand() {
  return (
    <section id="em-numeros" className="impact-band" aria-label="Silent Voice em números">
      <dl className="page-container impact-band__grid">
        {highlights.map(({ value, label }) => (
          <div className="impact-band__item" key={label}>
            <dt className="impact-band__label">{label}</dt>
            <dd className="impact-band__value">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
