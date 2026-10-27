import type {
  ConfirmedUtterance,
  ContextTranscriptEntry,
  LiveSessionPhase,
  LiveSessionState,
  ValidationLayer,
  ValidationLayerState,
} from '../types/live-session';

export const liveSessionPhases: LiveSessionPhase[] = [
  'idle',
  'ready',
  'capturing',
  'decoding',
  'candidate',
  'validating',
  'confirmed',
  'speaking',
  'needsRetry',
  'error',
];

const MOCK_DAY = Date.UTC(2026, 0, 1, 9, 41, 0);
const atSecond = (second: number) => MOCK_DAY + second * 1_000;

const contextEntries: ContextTranscriptEntry[] = [
  {
    id: 'context-water',
    timestamp: atSecond(10),
    text: 'Você quer água agora?',
  },
  {
    id: 'context-help',
    timestamp: atSecond(14),
    text: 'Posso te ajudar com alguma coisa?',
  },
];

const confirmedEntries: ConfirmedUtterance[] = [
  {
    id: 'confirmed-thirsty',
    timestamp: atSecond(10),
    text: 'Estou com sede',
  },
  { id: 'confirmed-yes', timestamp: atSecond(18), text: 'Sim' },
];

const layerLabels: Pick<ValidationLayer, 'id' | 'label'>[] = [
  { id: 'physicalAuthorization', label: 'Autorização física' },
  { id: 'neuromuscular', label: 'Neuromuscular' },
  { id: 'visual', label: 'Visual' },
  { id: 'contextual', label: 'Contextual' },
  { id: 'decision', label: 'Decisão' },
];

function validationLayersFor(phase: LiveSessionPhase): ValidationLayer[] {
  const states: ValidationLayerState[] =
    phase === 'validating'
      ? ['approved', 'approved', 'approved', 'validating', 'waiting']
      : phase === 'confirmed' || phase === 'speaking'
        ? ['approved', 'approved', 'approved', 'approved', 'approved']
        : phase === 'capturing'
          ? ['approved', 'waiting', 'waiting', 'waiting', 'waiting']
          : ['waiting', 'waiting', 'waiting', 'waiting', 'waiting'];

  return layerLabels.map((layer, index) => ({
    ...layer,
    state: states[index],
  }));
}

export function getContextWindow(
  entries: ContextTranscriptEntry[],
  now: number,
  duration = 10_000,
) {
  return entries.filter(
    (entry) => entry.timestamp >= now - duration && entry.timestamp <= now,
  );
}

export function createMockLiveSessionState(
  phase: LiveSessionPhase,
): LiveSessionState {
  const hasCandidate = [
    'candidate',
    'validating',
    'confirmed',
    'speaking',
  ].includes(phase);

  return {
    phase,
    candidate: hasCandidate ? 'Estou com sede' : undefined,
    confidence:
      phase === 'candidate' ? 78 : phase === 'validating' ? 92 : undefined,
    validationLayers: validationLayersFor(phase),
    contextWindow: getContextWindow(contextEntries, atSecond(19)),
    recentConfirmed:
      phase === 'confirmed' || phase === 'speaking'
        ? confirmedEntries
        : confirmedEntries.slice(0, 1),
  };
}

export function resolveLiveSessionPhase(value: string | string[] | undefined) {
  const phase = Array.isArray(value) ? value[0] : value;
  return liveSessionPhases.find((candidate) => candidate === phase);
}
