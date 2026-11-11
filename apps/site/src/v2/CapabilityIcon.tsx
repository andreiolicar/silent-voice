import type { AgentId } from './agents'

// Start at the top corner's midpoint so three equal dashes land on the vertices.
// Both silhouettes use this geometry, including its circular corner fillets.
const sensorTriangle = 'M12 4.95A1.5 1.5 0 0 1 13.299 5.7L18.495 14.7A1.5 1.5 0 0 1 17.196 16.95H6.804A1.5 1.5 0 0 1 5.505 14.7L10.701 5.7A1.5 1.5 0 0 1 12 4.95Z'

/** Solid silhouettes drawn for the capabilities selector. */
export function CapabilityIcon({ id }: { id: AgentId }) {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
    >
      {id === 'vision' && (
        <path d="M12 5C8.6 5 4.4 5.2 2.3 7.3.8 8.8.6 12.6 1.5 15.1c.7 1.9 2.1 3 4 3 2.6 0 4.2-2.8 6.5-2.8s3.9 2.8 6.5 2.8c1.9 0 3.3-1.1 4-3 .9-2.5.7-6.3-.8-7.8C19.6 5.2 15.4 5 12 5Z" />
      )}
      {id === 'audio' && (
        <>
          <path d="M12 2a10 10 0 0 0-10 10v5h2v-5a8 8 0 0 1 16 0v5h2v-5A10 10 0 0 0 12 2Z" />
          <rect x="2" y="12" width="7" height="10" rx="3.5" />
          <rect x="15" y="12" width="7" height="10" rx="3.5" />
        </>
      )}
      {id === 'emg' && (
        <>
          <path d={sensorTriangle} transform="translate(12 12.45) scale(.85) translate(-12 -12.45)" />
          <path
            d={sensorTriangle}
            transform="translate(12 12.45) scale(1.45) translate(-12 -12.45)"
            pathLength="90"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.1"
            strokeDasharray="16 14"
            strokeDashoffset="8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </>
      )}
    </svg>
  )
}
