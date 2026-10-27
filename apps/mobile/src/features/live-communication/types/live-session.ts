import type { SessionState } from '@/domain/device';

export type LiveSessionPhase = SessionState;

export type ValidationLayerState =
  'waiting' | 'validating' | 'approved' | 'rejected' | 'unavailable';

export type ValidationLayer = {
  id:
    | 'physicalAuthorization'
    | 'neuromuscular'
    | 'visual'
    | 'contextual'
    | 'decision';
  label: string;
  state: ValidationLayerState;
};

export type ContextTranscriptEntry = {
  id: string;
  timestamp: number;
  text: string;
};

export type ConfirmedUtterance = {
  id: string;
  timestamp: number;
  text: string;
};

export type LiveSessionState = {
  phase: LiveSessionPhase;
  candidate?: string;
  confidence?: number;
  validationLayers: ValidationLayer[];
  contextWindow: ContextTranscriptEntry[];
  recentConfirmed: ConfirmedUtterance[];
};
