import { LazyMotion, domAnimation } from 'motion/react'
import { LandingPage } from './LandingPage'
export function App() {
  return <LazyMotion features={domAnimation} strict><LandingPage /></LazyMotion>
}
