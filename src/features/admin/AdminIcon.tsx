type AdminIconName =
  | 'overview'
  | 'contacts'
  | 'mail'
  | 'file'
  | 'collapse'
  | 'organization'
  | 'chevron-right'
  | 'search'
  | 'chevron-down'
  | 'filter'
  | 'export'
  | 'close'
  | 'calendar'

export function AdminIcon({ name, className }: { name: AdminIconName; className?: string }) {
  return <img src={`/assets/admin/${name}.svg`} alt="" aria-hidden="true" className={className} />
}
