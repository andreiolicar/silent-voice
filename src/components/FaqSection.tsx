import * as m from 'motion/react-m'
import { useSectionEntrance } from '../entrance'
import { AccordionItem } from './ui/AccordionItem'
import { SectionEyebrow } from './SectionEyebrow'
import { SectionHeading } from './SectionHeading'
import { ContactCard } from './ContactCard'
import { ContactPill } from './ContactPill'
import './faq-section.css'

const questions = [
  {
    question: 'O que é o Silent Voice?',
    answer: 'O Silent Voice é uma solução de comunicação assistiva que transforma intenções em fala em tempo real. Combinando EMG, visão computacional e IA de borda, ele decodifica micro-sinais musculares em palavras e amplia as possibilidades de comunicação no dia a dia.',
  },
  {
    question: 'Como o Silent Voice funciona?',
    answer: 'A tecnologia combina sinais de EMG, visão computacional e inteligência artificial de borda. Esses recursos trabalham juntos para interpretar micro-sinais musculares e transformá-los em palavras.',
  },
  {
    question: 'Para quem ele foi pensado?',
    answer: 'Para quem busca mais autonomia na comunicação e para quem acompanha seu cuidado. A proposta é ampliar as possibilidades de conversa e conexão no dia a dia.',
  },
  {
    question: 'A resposta acontece em tempo real?',
    answer: 'O Silent Voice foi pensado para transformar intenções em fala em tempo real, com latência inferior a 300 ms, conforme a proposta apresentada nesta página.',
  },
  {
    question: 'O Silent Voice é um dispositivo vestível?',
    answer: 'Sim. A solução inclui um dispositivo vestível, que faz parte da experiência de comunicação assistiva do Silent Voice. Você pode conhecer seu design na seção de comunicação acima.',
  },
  {
    question: 'É preciso estar conectado à internet?',
    answer: 'A solução utiliza IA de borda. Para conhecer os requisitos de conexão e as condições de uso do dispositivo, fale com a nossa equipe.',
  },
  {
    question: 'Como posso conhecer melhor o Silent Voice?',
    answer: 'Escreva para contato@silentvoice.com.br para tirar dúvidas sobre disponibilidade, demonstrações e detalhes de uso. Nossa equipe pode ajudar você a conhecer a proposta do Silent Voice.',
  },
] as const

export function FaqSection() {
  const { ref, immediate, revealOnFocus, enter } = useSectionEntrance()

  return (
    <section ref={ref} id="faq" className="faq-section" aria-labelledby="faq-heading" onFocusCapture={revealOnFocus}>
      <div className="page-container faq-section__layout">
        <div className="faq-section__aside">
          <m.div className="faq-section__intro" {...enter(0)}>
            <div className="faq-section__heading-group">
              <SectionEyebrow>FAQ</SectionEyebrow>
              <SectionHeading id="faq-heading">Ainda tem dúvidas?</SectionHeading>
            </div>
            <ContactPill className="faq-pill" />
          </m.div>
          <ContactCard immediate={immediate} />
        </div>
        <div className="faq-section__questions">
          {questions.map((item, index) => (
            <m.div key={item.question} {...enter(.1 + index * .045)}>
              <AccordionItem title={item.question} number={`${String(index + 1).padStart(2, '0')}.`} defaultOpen={index === 0} divider={index < questions.length - 1}>
                <p>{item.answer}</p>
              </AccordionItem>
            </m.div>
          ))}
        </div>
      </div>
    </section>
  )
}
