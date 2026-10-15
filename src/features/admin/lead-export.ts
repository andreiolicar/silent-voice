import { statusLabels } from '../../../shared/leads'
import type { AdminLead, LeadProfile } from '../../../shared/leads'

const profileLabels: Record<LeadProfile, string> = {
  self: 'Para mim',
  family: 'Familiar ou cuidador',
  professional: 'Profissional de saúde',
  partner: 'Parceiro ou instituição',
}

function csvCell(value: string) {
  // Spreadsheet applications must treat visitor-supplied values as plain text.
  const safe = /^[\s\u0000-\u001f]*[=+@-]/.test(value) ? `'${value}` : value
  return `"${safe.replaceAll('"', '""')}"`
}

export function serializeLeadPage(leads: AdminLead[]): string {
  const rows = [
    ['Nome', 'E-mail', 'Objetivo', 'Status', 'Perfil', 'Organização', 'Recebido em'],
    ...leads.map((lead) => [
      lead.name, lead.email, lead.objective, statusLabels[lead.status],
      lead.profile ? profileLabels[lead.profile] : '', lead.organization ?? '', lead.createdAt,
    ]),
  ]
  return rows.map((row) => row.map(csvCell).join(',')).join('\r\n')
}

export function exportLeadPage(leads: AdminLead[]): void {
  const url = URL.createObjectURL(new Blob(['\uFEFF', serializeLeadPage(leads)], { type: 'text/csv;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `silent-voice-cadastros-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
