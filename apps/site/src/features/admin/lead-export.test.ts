import { describe, expect, it } from 'vitest'
import type { AdminLead } from '../../../shared/leads'
import { serializeLeadPage } from './lead-export'

const lead: AdminLead = {
  id: 'one', name: 'Ana, Souza', email: 'ana@example.test',
  objective: 'Conhecer "Silent Voice"\nEm família', profile: 'family',
  organization: 'Casa', status: 'new', version: 1, duplicateEmail: false,
  createdAt: '2026-10-15T12:00:00.000Z', updatedAt: '2026-10-15T12:00:00.000Z',
}

describe('contact page CSV export', () => {
  it('exports only supplied contacts with properly escaped fields and localized labels', () => {
    const csv = serializeLeadPage([lead])
    expect(csv).toContain('"Ana, Souza","ana@example.test","Conhecer ""Silent Voice""\nEm família"')
    expect(csv).toContain('"Novo","Familiar ou cuidador","Casa","2026-10-15T12:00:00.000Z"')
    expect(serializeLeadPage([]).split('\r\n')).toHaveLength(1)
  })

  it.each(['=HYPERLINK("x")', ' +1', '\t@SUM(A1)', '-1', '@value'])(
    'keeps untrusted spreadsheet formulas as text: %s', (value) => {
      const csv = serializeLeadPage([{ ...lead, name: value }])
      expect(csv).toContain(`"'${value.replaceAll('"', '""')}"`)
    },
  )
})
