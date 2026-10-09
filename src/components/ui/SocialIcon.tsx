export type SocialPlatform = 'instagram' | 'linkedin' | 'youtube'

export function SocialIcon({ platform }: { platform: SocialPlatform }) {
  return (
    <svg
      className="social-icon"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {platform === 'instagram' ? (
        <g
          stroke="currentColor"
          strokeWidth={1.7}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="3" y="3" width="18" height="18" rx="5" />
          <circle cx="12" cy="12" r="4" />
          <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
        </g>
      ) : platform === 'linkedin' ? (
        <g fill="currentColor">
          <circle cx="6" cy="5.5" r="1.7" />
          <rect x="4.5" y="9" width="3" height="11" />
          <path d="M10.5 9h3v1.5c.7-1 1.8-1.7 3.1-1.7 2.8 0 3.9 1.8 3.9 4.8V20h-3v-5.7c0-1.6-.3-2.7-1.8-2.7-1.6 0-2.2 1.1-2.2 2.7V20h-3V9Z" />
        </g>
      ) : (
        <>
          <rect
            x="2.5"
            y="5"
            width="19"
            height="14"
            rx="4"
            stroke="currentColor"
            strokeWidth={1.7}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path d="m10 8.5 6 3.5-6 3.5Z" fill="currentColor" />
        </>
      )}
    </svg>
  )
}
