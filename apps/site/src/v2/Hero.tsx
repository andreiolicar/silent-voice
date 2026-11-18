import type { CSSProperties } from 'react'
import { Typography } from '@silent-voice/web-ui/Typography'
import { agents, agentFor, agentSignalLabels } from './agents'
import { useHeroCarousel } from './useHeroCarousel'
import { StopwatchSymbol } from './StopwatchSymbol'
import { AgentPill } from './AgentPill'
export function Hero() {
  const {
    ref,
    selected,
    identity,
    leaving,
    cycle,
    running,
    selectPerson,
    next,
  } = useHeroCarousel()
  const agent = agentFor(selected)
  const badgeAgent = agentFor(identity)
  const others = agents.filter((person) => person.id !== selected)
  return (
    <section
      ref={ref}
      className="v2-hero"
      id="inteligencia"
      aria-labelledby="hero-heading"
      style={
        {
          '--agent-color': agent.color,
          '--agent-glow': agent.glow,
        } as CSSProperties
      }
    >
      <div className="v2-hero-copy">
        <StopwatchSymbol />
        <Typography as="h2" variant="h1" id="hero-heading" data-reveal="0">
          A nova era de agentes
          <br />
          de{' '}
          <img
            className="v2-ia-outline"
            src="/assets/v2/ia-badge.svg"
            alt="IA"
            width="59"
            height="38"
          />{' '}
          para dar voz.
        </Typography>
        <Typography as="p" variant="body" data-reveal="1">
          Inteligências que interpretam sinais musculares, movimentos e contexto
          para transformar a sua expressão em voz.
        </Typography>
        <a className="v2-button v2-button--gradient" href="#lista" data-reveal="2">
          Entrar na lista de espera
        </a>
      </div>
      <div className="v2-hero-cast" data-reveal="0">
        <div className="v2-hero-atmosphere" aria-hidden="true">
          {agents.map((person) => (
            <div
              key={person.id}
              className="v2-hero-atmosphere-layer"
              data-active={person.id === selected}
              style={{ '--agent-glow': person.glow } as CSSProperties}
            >
              <div className="v2-hero-halo" />
              <div className="v2-hero-rings" aria-hidden="true">
                <i />
                <i />
                <i />
                <i />
              </div>
            </div>
          ))}
          <div className="v2-hero-fade-top" />
        </div>
        {agents.map((person) => {
          const position =
            person.id === selected
              ? 'center'
              : person.id === others[0]?.id
                ? 'left'
                : 'right'
          return (
            <button
              type="button"
              key={person.id}
              className={`v2-hero-person v2-hero-person--${position}`}
              onClick={() => selectPerson(person.id)}
              aria-label={`Conhecer ${person.name}, ${person.label.toLowerCase()}`}
              aria-pressed={person.id === selected}
            >
              <img
                src={person.portrait}
                width="1254"
                height="1254"
                alt=""
                fetchPriority={person.id === 'emg' ? 'high' : 'auto'}
              />
            </button>
          )
        })}
        <div className="v2-hero-fade" aria-hidden="true" />
        <div
          className="v2-hero-identity"
          data-leaving={leaving}
          style={{ '--agent-color': badgeAgent.color } as CSSProperties}
        >
          <AgentPill
            agentId={identity}
            crossfadeAvatar
            onClick={next}
            ariaLabel={`Próximo agente. ${badgeAgent.name}, ${agentSignalLabels[badgeAgent.id]}`}
          />
          <span className="v2-hero-active-mark" aria-hidden="true">
            <span className="v2-hero-progress-track">
              <span
                key={`${cycle}-${running}`}
                className={`v2-hero-progress${running ? ' v2-hero-progress--running' : ''}`}
              />
            </span>
          </span>
        </div>
      </div>
    </section>
  )
}
