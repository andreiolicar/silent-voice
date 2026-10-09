import { createContext, useContext, useSyncExternalStore } from 'react'
import type { ReactNode } from 'react'

type IntroPhase = 'holding' | 'revealing' | 'complete'
type IntroState = { ready: boolean; immediate: boolean }

declare global {
  interface Window {
    __silentVoiceIntro?: {
      readonly phase: IntroPhase
      readonly immediate: boolean
      heroReady(): void
      finish(): void
    }
  }
}

const IntroContext = createContext<IntroState>({ ready: true, immediate: false })
const eventName = 'silentvoice:intro-state'

function subscribe(onChange: () => void) {
  window.addEventListener(eventName, onChange)
  return () => window.removeEventListener(eventName, onChange)
}

function getPhase(): IntroPhase {
  return window.__silentVoiceIntro?.phase ?? 'complete'
}

export function IntroProvider({ children }: { children: ReactNode }) {
  const phase = useSyncExternalStore(subscribe, getPhase, () => 'complete')
  return (
    <IntroContext.Provider value={{ ready: phase !== 'holding', immediate: window.__silentVoiceIntro?.immediate ?? false }}>
      {children}
    </IntroContext.Provider>
  )
}

export function useIntroState() {
  return useContext(IntroContext)
}

export function notifyHeroReady() {
  window.__silentVoiceIntro?.heroReady()
}
