import { useState } from 'react'
import { Typography } from '@silent-voice/web-ui/Typography'
import * as m from 'motion/react-m'
import { useReducedMotionPreference } from '../entrance'
import './faq.css'

const questions = [
  {
    question: 'O que é o Silent Voice?',
    answer: 'O Silent Voice combina uma neckband e inteligência artificial para interpretar sinais musculares, movimentos dos lábios e o contexto da conversa, ajudando a transformar sua expressão em voz.',
  },
  {
    question: 'Para quem ele foi pensado?',
    answer: 'Para pessoas que buscam mais autonomia na comunicação e para quem acompanha seu cuidado. A proposta é ampliar as possibilidades de conversa e conexão no dia a dia.',
  },
  {
    question: 'Como o dispositivo funciona?',
    answer: 'A neckband reúne um sensor de sinais musculares, uma câmera e um microfone. Os núcleos de inteligência combinam essas informações para ajudar a reconhecer as palavras que você articula.',
  },
  {
    question: 'Quem são Caio, Lia e Ravi?',
    answer: 'São as representações dos três núcleos de inteligência do Silent Voice. Caio acompanha os movimentos dos lábios, Lia interpreta os sinais musculares e Ravi acrescenta o contexto da conversa.',
  },
  {
    question: 'O que o sensor muscular capta?',
    answer: 'Ao articular, os músculos da face geram atividade elétrica. O sensor EMG capta esses sinais, e Lia os interpreta como pistas para reconhecer o que você quer dizer.',
  },
  {
    question: 'Qual é o papel da câmera?',
    answer: 'A câmera acompanha o contorno e a abertura dos lábios. Caio interpreta esses movimentos e acrescenta informações visuais aos sinais captados pelo dispositivo.',
  },
  {
    question: 'Para que serve o microfone?',
    answer: 'O microfone capta o contexto sonoro da conversa. Ravi usa essas informações para complementar os sinais musculares e visuais e ajudar a interpretar sua resposta.',
  },
  {
    question: 'Como a expressão ganha voz?',
    answer: 'Os núcleos de inteligência trabalham juntos no reconhecimento das palavras articuladas. O alto-falante do dispositivo reproduz essas palavras em áudio.',
  },
  {
    question: 'Como posso acompanhar os próximos passos?',
    answer: <>Entre na <a href="#lista">lista de interesse</a> para acompanhar as novidades e os próximos passos do Silent Voice.</>,
  },
  {
    question: 'Como posso falar com a equipe?',
    answer: <>Envie sua dúvida para <a href="mailto:contato@silentvoice.com.br">contato@silentvoice.com.br</a>. Nossa equipe pode ajudar você a conhecer melhor a proposta do Silent Voice.</>,
  },
]

export function Faq() {
  const [expanded, setExpanded] = useState<number | null>(0)
  const reducedMotion = useReducedMotionPreference()

  return (
    <section id="faq" className="v2-faq" aria-labelledby="faq-title">
      <div className="v2-faq-layout">
        <div className="v2-faq-head">
          <Typography as="h2" variant="h2" id="faq-title" className="v2-faq-title" data-reveal="0">Perguntas frequentes</Typography>
          <Typography as="p" variant="body" className="v2-faq-lead" data-reveal="1">Tudo o que você precisa saber sobre essa nova forma de se comunicar.</Typography>
        </div>
        <div className="v2-faq-list">
          {questions.map(({ question, answer }, index) => {
            const open = expanded === index
            return (
              <div className="v2-faq-item" data-reveal="0" data-expanded={open ? '' : undefined} key={question}>
                <Typography as="h3" variant="body" weight="semibold" className="v2-faq-question">
                  <button
                    type="button"
                    className="v2-faq-trigger"
                    id={`faq-question-${index}`}
                    aria-expanded={open}
                    aria-controls={`faq-answer-${index}`}
                    onClick={() => setExpanded(open ? null : index)}
                  >
                    <span className="v2-faq-ask">
                      <span className="v2-faq-dot" aria-hidden="true" />
                      <span>{question}</span>
                    </span>
                    <svg className="v2-faq-sign" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="4.8" strokeLinecap="round" aria-hidden="true">
                      <path d="M10 24H38" />
                      <path className="v2-faq-bar" d="M24 10V38" />
                    </svg>
                  </button>
                </Typography>
                <m.div
                  className="v2-faq-answer-wrap"
                  id={`faq-answer-${index}`}
                  aria-labelledby={`faq-question-${index}`}
                  aria-hidden={!open}
                  inert={!open}
                  initial={false}
                  animate={{ height: open ? 'auto' : 0 }}
                  transition={{ duration: reducedMotion ? 0 : .32, ease: [.22, 1, .36, 1] }}
                >
                  <Typography as="p" variant="body" className="v2-faq-answer">{answer}</Typography>
                </m.div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
