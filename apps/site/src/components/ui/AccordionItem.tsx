import { useId, useState } from 'react'
import type { ReactNode } from 'react'
import * as m from 'motion/react-m'
import { useReducedMotionPreference } from '../../entrance'
import './accordion-item.css'

type AccordionItemProps = {
  title: string
  number?: string
  defaultOpen?: boolean
  divider?: boolean
  children: ReactNode
}

export function AccordionItem({ title, number, defaultOpen = false, divider = true, children }: AccordionItemProps) {
  const id = useId()
  const [open, setOpen] = useState(defaultOpen)
  const reducedMotion = useReducedMotionPreference()

  return (
    <div className="accordion-item" data-divider={divider}>
      <h3>
        <button id={`${id}-question`} className="accordion-item__question" type="button" aria-expanded={open} aria-controls={`${id}-answer`} onClick={() => setOpen(value => !value)}>
          {number && <span className="accordion-item__number" aria-hidden="true">{number}</span>}
          <span className="accordion-item__label">{title}</span>
          <svg className="accordion-item__toggle" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" aria-hidden="true" focusable="false">
            <path d="M5 12h14" />
            <m.path d="M12 5v14" initial={false} animate={{ opacity: open ? 0 : 1 }} transition={{ duration: reducedMotion ? 0 : .18 }} />
          </svg>
        </button>
      </h3>
      <m.div id={`${id}-answer`} className="accordion-item__answer" aria-labelledby={`${id}-question`} aria-hidden={!open} inert={!open}
        initial={false} animate={{ height: open ? 'auto' : 0, opacity: open ? 1 : 0 }} transition={{ duration: reducedMotion ? 0 : .32, ease: [.2, .8, .2, 1] }}>
        <div className="accordion-item__content">{children}</div>
      </m.div>
    </div>
  )
}
