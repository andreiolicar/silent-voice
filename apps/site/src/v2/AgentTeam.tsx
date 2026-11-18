import { useEffect, type CSSProperties } from "react";
import { Typography } from "@silent-voice/web-ui/Typography";
import { AgentTabs, agentIcons } from "./AgentTabs";
import { agents, agentFor, type AgentId } from "./agents";
import { AgentDemo } from "./AgentDemo";
import { useAgentCarousel } from "./useAgentCarousel";
export function AgentTeam({ requestedAgent }: { requestedAgent?: { id: AgentId } }) {
  const { ref, selected, cycle, select, running, reducedMotion } =
    useAgentCarousel();
  useEffect(() => {
    if (requestedAgent) select(requestedAgent.id);
  }, [requestedAgent, select]);
  const agent = agentFor(selected);
  const Icon = agentIcons[selected];
  return (
    <section
      ref={ref}
      className="v2-team v2-section"
      id="equipe"
      tabIndex={-1}
      aria-labelledby="team-title"
      style={
        {
          "--agent-color": agent.color,
          "--agent-tint": agent.tint,
        } as CSSProperties
      }
    >
      <div className="v2-section-intro">
        <Typography as="h2" variant="h1" id="team-title" data-reveal="0">
          Uma equipe de IA trabalhando
          <br className="v2-desktop-break" /> pela sua expressão.
        </Typography>
        <Typography as="p" variant="body" data-reveal="1">
          Assistentes especializados em interpretar sinais musculares,
          movimentos e o contexto da conversa.
        </Typography>
      </div>
      <AgentTabs
        value={selected}
        onChange={select}
        prefix="team"
        portraits
        progress={{ cycle, running }}
      />
      <div className={`v2-agent-panel v2-agent-panel--${selected}`} data-reveal="0">
        <div
          id="team-panel"
          role="tabpanel"
          tabIndex={0}
          aria-labelledby={`team-tab-${selected}`}
          className="v2-agent-inner"
        >
          {agents.map((person) => (
            <div
              key={person.id}
              className="v2-agent-slide"
              aria-hidden={selected !== person.id}
              inert={selected !== person.id}
              style={
                {
                  "--agent-color": person.color,
                  "--agent-tint": person.tint,
                } as CSSProperties
              }
            >
              <div className="v2-agent-copy">
                <span className="v2-agent-kicker">
                  {person.name}{" "}
                  <img
                    src={`/assets/v2/ia-badge-${person.id === "emg" ? "green" : person.id === "audio" ? "pink" : "blue"}.svg`}
                    alt="IA"
                    width="19"
                    height="12"
                  />
                </span>
                <Typography as="h3" variant="h3">{person.title}</Typography>
                <Typography as="p" variant="body">{person.description}</Typography>
              </div>
              <AgentDemo
                key={selected === person.id ? cycle : "idle"}
                id={person.id}
                running={running && selected === person.id}
                immediate={reducedMotion}
              />
            </div>
          ))}
        </div>
        <div className="v2-panel-caption">
          <Icon size={16} aria-hidden="true" />
          <span>{agent.detail}</span>
        </div>
      </div>
    </section>
  );
}
