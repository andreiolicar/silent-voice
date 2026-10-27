export const leadStatuses = [
  'new',
  'contacted',
  'demo_scheduled',
  'closed',
] as const
export type LeadStatus = (typeof leadStatuses)[number]
export type LeadProfile = 'self' | 'family' | 'professional' | 'partner'
export type LeadInput = {
  name: string
  email: string
  objective: string
  profile?: LeadProfile
  organization?: string
}
export type LeadReceipt = { id: string; createdAt: string }
export type AdminLead = LeadInput &
  LeadReceipt & {
    status: LeadStatus
    version: number
    updatedAt: string
    duplicateEmail: boolean
  }
export type LeadNote = {
  id: string
  text: string
  author: string
  createdAt: string
}
export type LeadDetail = { lead: AdminLead; notes: LeadNote[] }
export type LeadList = {
  items: AdminLead[]
  total: number
  page: number
  counts: Record<LeadStatus, number>
}
export const statusLabels: Record<LeadStatus, string> = {
  new: 'Novo',
  contacted: 'Em contato',
  demo_scheduled: 'Demonstração combinada',
  closed: 'Encerrado',
}
