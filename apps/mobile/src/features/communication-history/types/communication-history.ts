export type CommunicationHistoryEntry = {
  confirmedAt: Date | string;
  id: string;
  text: string;
};

export type CommunicationHistoryGroup = {
  dateKey: string;
  entries: CommunicationHistoryEntry[];
  label: string;
};
