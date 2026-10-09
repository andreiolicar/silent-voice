import { siteLinks } from './site-links'
import type { AiProvider } from './components/ui/AiProviderIcon'
import type { SocialPlatform } from './components/ui/SocialIcon'

type FooterLink = {
  label: string
  href?: string
  external?: boolean
}

export const footerColumns: readonly { title: string; links: readonly FooterLink[] }[] = [
  {
    title: 'Produto',
    links: [
      { label: 'Comunicação assistiva', href: siteLinks.comunicacao },
      { label: 'Por dentro do app', href: siteLinks.aplicativo },
      { label: 'Para quem', href: siteLinks.paraQuem },
      { label: 'Perguntas frequentes', href: siteLinks.faq },
    ],
  },
  {
    title: 'Legal',
    links: [
      { label: 'Termos de uso', href: siteLinks.termos, external: true },
      { label: 'Privacidade', href: siteLinks.privacidade, external: true },
    ],
  },
]

// These links carry context from this page, without relying on a public URL or
// implying that a provider has verified the product's capabilities.
const aiQuestion = [
  'Quero entender a proposta do Silent Voice: comunicação assistiva com EMG, visão computacional e IA de borda para transformar intenções em fala.',
  'Explique a proposta e esses termos em linguagem simples.',
  'Que perguntas devo fazer à equipe para entender disponibilidade, demonstrações e requisitos de uso?',
  'Não suponha informações que não foram fornecidas.',
].join(' ')

const question = encodeURIComponent(aiQuestion)

export const footerAiLinks: readonly { provider: AiProvider; label: string; accessibleLabel: string; href: string }[] = [
  { provider: 'chatgpt', label: 'ChatGPT', accessibleLabel: 'Pergunte ao ChatGPT sobre o Silent Voice', href: `https://chatgpt.com/?q=${question}` },
  { provider: 'claude', label: 'Claude', accessibleLabel: 'Pergunte ao Claude sobre o Silent Voice', href: `https://claude.ai/new?q=${question}` },
  { provider: 'gemini', label: 'Gemini', accessibleLabel: 'Pergunte sobre o Silent Voice no Modo IA do Google', href: `https://www.google.com/search?udm=50&q=${question}` },
  { provider: 'perplexity', label: 'Perplexity', accessibleLabel: 'Pergunte ao Perplexity sobre o Silent Voice', href: `https://www.perplexity.ai/search?q=${question}` },
  { provider: 'grok', label: 'Grok', accessibleLabel: 'Pergunte ao Grok sobre o Silent Voice', href: `https://grok.com/?q=${question}` },
]

export const footerSocialLinks: readonly { platform: SocialPlatform; label: string; href?: string; text?: string }[] = [
  { platform: 'instagram', label: 'Instagram do Silent Voice', href: siteLinks.instagram, text: 'Siga o Silent Voice' },
  { platform: 'linkedin', label: 'LinkedIn do Silent Voice', href: siteLinks.linkedin },
  { platform: 'youtube', label: 'YouTube do Silent Voice', href: siteLinks.youtube },
]
