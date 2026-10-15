import { createContext, useContext } from 'react'
import { createLibrary, defineComponent } from '@openuidev/react-lang'
import { Card } from '@openuidev/react-ui/Card'
import { Steps, StepsItem } from '@openuidev/react-ui/Steps'
import { Button } from '@openuidev/react-ui/Button'
import { z } from 'zod/v4'

export const ContactContext = createContext<() => void>(() => {})
const text = (value: unknown, max: number) =>
  typeof value === 'string' ? value.slice(0, max) : ''
const StepSchema = z.object({
  title: z.string().max(90),
  detail: z.string().max(350),
})
const Text = defineComponent({
  name: 'Text',
  description: 'Texto curto em português, sem HTML ou Markdown.',
  props: z.object({ text: z.string().max(1200) }),
  component: ({ props }) => (
    <p className="sv-response-text">{text(props.text, 1200)}</p>
  ),
})
const HowTo = defineComponent({
  name: 'HowTo',
  description: 'Até cinco passos curtos com título e explicação.',
  props: z.object({ items: z.array(StepSchema).max(5) }),
  component: ({ props }) => (
    <Steps>
      {(Array.isArray(props.items) ? props.items : [])
        .slice(0, 5)
        .map((item, i) => {
          const parsed = StepSchema.safeParse(item)
          return parsed.success ? (
            <StepsItem
              key={i}
              number={i + 1}
              title={parsed.data.title}
              details={parsed.data.detail}
            />
          ) : null
        })}
    </Steps>
  ),
})
const BulletList = defineComponent({
  name: 'BulletList',
  description: 'Até seis itens de texto simples, sem links ou HTML.',
  props: z.object({ items: z.array(z.string().max(250)).max(6) }),
  component: ({ props }) => (
    <ul className="sv-response-list">
      {(Array.isArray(props.items) ? props.items : [])
        .slice(0, 6)
        .map((item, i) =>
          typeof item === 'string' ? <li key={i}>{text(item, 250)}</li> : null
        )}
    </ul>
  ),
})
function LocalContact() {
  const openContact = useContext(ContactContext)
  return (
    <Button
      type="button"
      size="small"
      variant="secondary"
      onClick={openContact}
    >
      Conversar com a equipe
    </Button>
  )
}
const ContactAction = defineComponent({
  name: 'ContactAction',
  description:
    'Abre somente o formulário de contato local. Não recebe URL, destino ou ação.',
  props: z.object({}),
  component: LocalContact,
})
const allowedChildren = new Set([
  'Text',
  'HowTo',
  'BulletList',
  'ContactAction',
])
const Answer = defineComponent({
  name: 'Answer',
  description:
    'Uma resposta curta com título e até oito blocos. Não pode conter outro Answer.',
  props: z.object({
    title: z.string().max(100),
    children: z
      .array(z.union([Text.ref, HowTo.ref, BulletList.ref, ContactAction.ref]))
      .max(8),
  }),
  component: ({ props, renderNode }) => {
    const children = (Array.isArray(props.children) ? props.children : [])
      .slice(0, 8)
      .filter(
        (child) =>
          child &&
          typeof child === 'object' &&
          'typeName' in child &&
          allowedChildren.has(String(child.typeName))
      )
    return (
      <Card variant="card" width="full">
        <h3 className="sv-response-title">{text(props.title, 100)}</h3>
        {renderNode(children)}
      </Card>
    )
  },
})
export const silentVoiceLibrary = createLibrary({
  root: 'Answer',
  components: [Answer, Text, HowTo, BulletList, ContactAction],
})
