import type {
  CommunicationHistoryEntry,
  CommunicationHistoryGroup,
} from '../types/communication-history';

const dateFormatter = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: 'long',
});

const timeFormatter = new Intl.DateTimeFormat('pt-BR', {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

function startOfDay(value: Date | string) {
  const date = new Date(value);
  date.setHours(0, 0, 0, 0);
  return date;
}

function dateKey(value: Date | string) {
  const date = startOfDay(value);
  return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;
}

function dateLabel(value: Date | string, now: Date) {
  const date = startOfDay(value);
  const today = startOfDay(now);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (date.getTime() === today.getTime()) return 'Hoje';
  if (date.getTime() === yesterday.getTime()) return 'Ontem';
  return dateFormatter.format(date);
}

export function formatCommunicationTime(value: Date | string) {
  return timeFormatter.format(new Date(value));
}

export function groupCommunicationHistory(
  entries: CommunicationHistoryEntry[],
  now = new Date(),
): CommunicationHistoryGroup[] {
  const sorted = [...entries].sort(
    (left, right) =>
      new Date(right.confirmedAt).getTime() -
      new Date(left.confirmedAt).getTime(),
  );
  const groups = new Map<string, CommunicationHistoryGroup>();

  sorted.forEach((entry) => {
    const key = dateKey(entry.confirmedAt);
    const group = groups.get(key);

    if (group) group.entries.push(entry);
    else {
      groups.set(key, {
        dateKey: key,
        entries: [entry],
        label: dateLabel(entry.confirmedAt, now),
      });
    }
  });

  return [...groups.values()];
}
