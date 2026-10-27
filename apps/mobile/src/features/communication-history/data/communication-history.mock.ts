import type { CommunicationHistoryEntry } from '../types/communication-history';

function dateAt(dayOffset: number, hours: number, minutes: number) {
  const date = new Date();
  date.setHours(hours, minutes, 0, 0);
  date.setDate(date.getDate() + dayOffset);
  return date.toISOString();
}

export const communicationHistoryMock: CommunicationHistoryEntry[] = [
  {
    id: 'confirmed-1',
    text: 'Estou com sede',
    confirmedAt: dateAt(0, 14, 32),
  },
  {
    id: 'confirmed-2',
    text: 'Pode me ajudar?',
    confirmedAt: dateAt(0, 14, 28),
  },
  { id: 'confirmed-3', text: 'Sim', confirmedAt: dateAt(0, 13, 51) },
  { id: 'confirmed-4', text: 'Obrigado', confirmedAt: dateAt(-1, 18, 4) },
];
