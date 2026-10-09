import './showcase-backdrop.css'

/** Shared decorative background for the device and app cards. */
export function ShowcaseBackdrop() {
  return (
    <svg className="showcase-backdrop" viewBox="0 0 471 440" aria-hidden="true">
      <g fill="none" stroke="var(--color-surface)" strokeOpacity=".36" strokeWidth="1">
        <circle cx="235.5" cy="220" r="108" />
        <circle cx="235.5" cy="220" r="166" />
        <circle cx="235.5" cy="220" r="224" />
      </g>
      <g fill="var(--color-surface)" fillOpacity=".7">
        <circle cx="352.9" cy="102.6" r="4" />
        <circle cx="91.7" cy="303" r="3" />
        <circle cx="177.5" cy="3.6" r="3" />
      </g>
      <g fill="var(--color-surface)" fillOpacity=".35">
        <circle cx="392" cy="48" r="1.5" />
        <circle cx="404" cy="48" r="1.5" />
        <circle cx="416" cy="48" r="1.5" />
        <circle cx="392" cy="60" r="1.5" />
        <circle cx="404" cy="60" r="1.5" />
        <circle cx="416" cy="60" r="1.5" />
      </g>
    </svg>
  )
}
