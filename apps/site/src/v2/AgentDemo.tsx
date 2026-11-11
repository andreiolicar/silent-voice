import { CardIllustration } from "../components/cards/CardIllustration";
import type { AgentId } from "./agents";
import "./agent-demo.css";

// Reuse the published landing's SVG artwork and its original animation curves.
export function AgentDemo({
  id,
  running,
  immediate,
}: {
  id: AgentId;
  running: boolean;
  immediate: boolean;
}) {
  return (
    <div
      className={`v2-agent-demo v2-agent-demo--${id}`}
      aria-hidden="true"
      data-running={running}
    >
      <CardIllustration
        kind={
          id === "vision"
            ? "care"
            : id === "emg"
              ? "technology"
              : "communication"
        }
        variant={id === "vision" ? "vision" : undefined}
        metric={id === "emg" ? "EMG" : undefined}
        active={running || immediate}
        running={running}
        immediate={immediate}
      />
    </div>
  );
}
