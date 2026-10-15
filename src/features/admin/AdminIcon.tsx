import {
  Building2,
  CalendarCheck,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  CircleDot,
  Download,
  FileText,
  LayoutDashboard,
  ListFilter,
  LogOut,
  Mail,
  MessagesSquare,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCw,
  Search,
  UsersRound,
  X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const icons = {
  overview: LayoutDashboard,
  contacts: UsersRound,
  mail: Mail,
  file: FileText,
  collapse: PanelLeftClose,
  expand: PanelLeftOpen,
  organization: Building2,
  'chevron-right': ChevronRight,
  search: Search,
  'chevron-down': ChevronDown,
  filter: ListFilter,
  export: Download,
  close: X,
  calendar: CalendarDays,
  'status-new': CircleDot,
  'status-contacted': MessagesSquare,
  'status-demo': CalendarCheck,
  'status-closed': CircleCheck,
  logout: LogOut,
  refresh: RefreshCw,
} satisfies Record<string, LucideIcon>

export type AdminIconName = keyof typeof icons

export function AdminIcon({ name, className }: { name: AdminIconName; className?: string }) {
  const Icon = icons[name]
  return (
    <Icon
      size={16}
      strokeWidth={1.65}
      color="currentColor"
      aria-hidden="true"
      focusable={false}
      className={`crm-icon${className ? ` ${className}` : ''}`}
    />
  )
}
