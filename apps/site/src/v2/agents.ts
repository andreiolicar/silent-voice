export type AgentId = "emg" | "vision" | "audio";
export const agentSignalLabels: Record<AgentId, string> = {
  vision: "Movimentos dos lábios",
  emg: "Sinais musculares",
  audio: "Contexto da conversa",
};
export const agents = [
  {
    id: "vision",
    name: "Caio",
    label: "Visão computacional",
    short: "Visão",
    color: "#0E7AFF",
    tint: "#E7F2FF",
    glow: "#9FCAFF",
    portrait: "/assets/v2/caio.webp",
    bentoPortrait: "/assets/v2/caio-bento-brand.webp",
    bentoPortraitHeight: 916,
    title: "Os movimentos ganham significado.",
    description:
      "A câmera acompanha o contorno e a abertura dos lábios. Caio transforma esses movimentos em pistas para reconhecer as palavras que você articula.",
    capability: "Observa cada movimento.",
    capabilityCopy:
      "A câmera acompanha os lábios e interpreta os movimentos que participam da formação das palavras.",
    detail: "Leitura visual da articulação",
    number: "01",
  },
  {
    id: "emg",
    name: "Lia",
    label: "Sinais musculares",
    short: "Sinais musculares",
    color: "var(--color-brand)",
    tint: "color-mix(in srgb, var(--color-brand) 10%, white)",
    glow: "color-mix(in srgb, var(--color-brand) 40%, white)",
    portrait: "/assets/v2/lia-brand.webp",
    bentoPortrait: "/assets/v2/lia-bento-refined.webp",
    bentoPortraitHeight: 895,
    title: "A expressão começa antes da voz.",
    description:
      "Ao articular, seus músculos geram sinais. Lia interpreta essa atividade captada pela neckband para ajudar a transformar sua expressão em palavras.",
    capability: "Sente a sua articulação.",
    capabilityCopy:
      "Os sinais elétricos dos músculos acrescentam uma camada de informação àquilo que você articula.",
    detail: "Reconhecimento dos sinais musculares",
    number: "02",
  },
  {
    id: "audio",
    name: "Ravi",
    label: "Áudio e contexto",
    short: "Áudio e contexto",
    color: "#EC4899",
    tint: "#FCE7F3",
    glow: "#FCA9DF",
    portrait: "/assets/v2/ravi.webp",
    bentoPortrait: "/assets/v2/ravi-bento-silver.webp",
    bentoPortraitHeight: 979,
    title: "Toda conversa tem um contexto.",
    description:
      "Água ou café? Ravi acompanha o assunto da conversa e acrescenta contexto aos sinais musculares e visuais para ajudar a interpretar sua resposta.",
    capability: "Escuta além de uma palavra.",
    capabilityCopy:
      "O contexto da conversa complementa os sinais musculares e visuais, ajudando a interpretar a articulação.",
    detail: "Compreensão do contexto da conversa",
    number: "03",
  },
] as const;
export function agentFor(id: AgentId) {
  return agents.find((agent) => agent.id === id)!;
}
