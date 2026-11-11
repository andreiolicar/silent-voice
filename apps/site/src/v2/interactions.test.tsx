import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { AgentTeam } from "./AgentTeam";
import { Hero } from "./Hero";
import { Capabilities } from "./Capabilities";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

it("cycles capabilities in five seconds, ignores hover and keeps the current interval when reselected", () => {
  vi.useFakeTimers();
  render(<Capabilities />);
  const vision = screen.getByRole("tab", { name: "Visão computacional" });
  const emg = screen.getByRole("tab", { name: "Sinais musculares" });
  const audio = screen.getByRole("tab", { name: "Áudio e contexto" });
  act(() => vi.advanceTimersByTime(2000));
  fireEvent.mouseEnter(audio);
  audio.focus();
  expect(vision).toHaveAttribute("aria-selected", "true");
  fireEvent.click(vision);
  act(() => vi.advanceTimersByTime(2999));
  expect(vision).toHaveAttribute("aria-selected", "true");
  act(() => vi.advanceTimersByTime(1));
  expect(emg).toHaveAttribute("aria-selected", "true");
  act(() => vi.advanceTimersByTime(5000));
  expect(audio).toHaveAttribute("aria-selected", "true");
  act(() => vi.advanceTimersByTime(5000));
  expect(vision).toHaveAttribute("aria-selected", "true");
  act(() => vi.advanceTimersByTime(3500));
  fireEvent.click(audio);
  expect(screen.getByRole("tabpanel")).toHaveAttribute(
    "aria-labelledby",
    audio.id,
  );
  expect(screen.getByRole("tabpanel")).toHaveTextContent(
    "Escuta além de uma palavra.",
  );
  act(() => vi.advanceTimersByTime(4999));
  expect(audio).toHaveAttribute("aria-selected", "true");
  act(() => vi.advanceTimersByTime(1));
  expect(vision).toHaveAttribute("aria-selected", "true");
});

it("lets keyboard users select capabilities without an extra focus reset", async () => {
  vi.useFakeTimers();
  render(<Capabilities />);
  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  const vision = screen.getByRole("tab", { name: "Visão computacional" });
  const emg = screen.getByRole("tab", { name: "Sinais musculares" });
  const audio = screen.getByRole("tab", { name: "Áudio e contexto" });
  vision.focus();
  await user.keyboard("{ArrowDown}");
  expect(emg).toHaveFocus();
  expect(emg).toHaveAttribute("aria-selected", "true");
  await user.keyboard("{End}");
  expect(audio).toHaveFocus();
  expect(audio).toHaveAttribute("aria-selected", "true");
  await user.keyboard("{Home}");
  expect(vision).toHaveFocus();
  expect(vision).toHaveAttribute("aria-selected", "true");
});

it("keeps capabilities manual when reduced motion is preferred", () => {
  vi.useFakeTimers();
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query) =>
      ({
        matches: true,
        media: query,
        onchange: null,
        addEventListener() {},
        removeEventListener() {},
        addListener() {},
        removeListener() {},
        dispatchEvent() {
          return true;
        },
      }) as MediaQueryList,
  );
  render(<Capabilities />);
  const vision = screen.getByRole("tab", { name: "Visão computacional" });
  const audio = screen.getByRole("tab", { name: "Áudio e contexto" });
  act(() => vi.advanceTimersByTime(15000));
  expect(vision).toHaveAttribute("aria-selected", "true");
  fireEvent.click(audio);
  act(() => vi.advanceTimersByTime(15000));
  expect(audio).toHaveAttribute("aria-selected", "true");
});

it("stops the capability cycle in a hidden page and restarts a full interval on return", () => {
  vi.useFakeTimers();
  const hidden = vi.spyOn(document, "hidden", "get").mockReturnValue(false);
  render(<Capabilities />);
  const vision = screen.getByRole("tab", { name: "Visão computacional" });
  const emg = screen.getByRole("tab", { name: "Sinais musculares" });
  act(() => vi.advanceTimersByTime(3000));
  hidden.mockReturnValue(true);
  fireEvent(document, new Event("visibilitychange"));
  act(() => vi.advanceTimersByTime(15000));
  expect(vision).toHaveAttribute("aria-selected", "true");
  hidden.mockReturnValue(false);
  fireEvent(document, new Event("visibilitychange"));
  act(() => vi.advanceTimersByTime(4999));
  expect(vision).toHaveAttribute("aria-selected", "true");
  act(() => vi.advanceTimersByTime(1));
  expect(emg).toHaveAttribute("aria-selected", "true");
});

it("selects agents on activation, never hover or pointer-down, and preserves keyboard navigation", async () => {
  render(<AgentTeam />);
  const user = userEvent.setup();
  const emg = screen.getByRole("tab", { name: /Sinais musculares/ });
  const vision = screen.getByRole("tab", { name: /Visão computacional/ });
  const audio = screen.getByRole("tab", { name: /Áudio e contexto/ });
  expect(vision).toHaveAttribute("aria-selected", "true");
  vision.focus();
  await user.keyboard("{ArrowRight}");
  expect(emg).toHaveFocus();
  await user.keyboard("{ArrowLeft}");
  expect(vision).toHaveFocus();
  expect(vision).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tabpanel")).toHaveAttribute(
    "aria-labelledby",
    vision.id,
  );
  expect(screen.getByRole("tabpanel")).toHaveTextContent(
    "Os movimentos ganham significado.",
  );
  await user.click(audio);
  expect(audio).toHaveAttribute("aria-selected", "true");
  fireEvent.mouseEnter(emg);
  expect(audio).toHaveAttribute("aria-selected", "true");
  await user.pointer({ target: emg, keys: "[MouseLeft>]" });
  expect(audio).toHaveAttribute("aria-selected", "true");
  await user.pointer({ target: emg, keys: "[/MouseLeft]" });
  expect(emg).toHaveAttribute("aria-selected", "true");
  emg.focus();
  await user.keyboard("{End}");
  expect(audio).toHaveFocus();
  await user.keyboard("{Home}");
  expect(vision).toHaveFocus();
});

it("cycles every five seconds and restarts the full interval after clicking even the current agent", () => {
  vi.useFakeTimers();
  render(<AgentTeam />);
  const vision = screen.getByRole("tab", { name: /Visão computacional/ });
  const emg = screen.getByRole("tab", { name: /Sinais musculares/ });
  const audio = screen.getByRole("tab", { name: /Áudio e contexto/ });
  act(() => vi.advanceTimersByTime(5000));
  expect(emg).toHaveAttribute("aria-selected", "true");
  act(() => vi.advanceTimersByTime(4000));
  fireEvent.click(emg);
  act(() => vi.advanceTimersByTime(4999));
  expect(emg).toHaveAttribute("aria-selected", "true");
  act(() => vi.advanceTimersByTime(1));
  expect(audio).toHaveAttribute("aria-selected", "true");
  act(() => vi.advanceTimersByTime(5000));
  expect(vision).toHaveAttribute("aria-selected", "true");
});

it("runs only the selected demonstration and pauses it while the page is hidden", () => {
  vi.useFakeTimers();
  const hidden = vi.spyOn(document, "hidden", "get").mockReturnValue(false);
  const { container } = render(<AgentTeam />);
  const runningDemos = () =>
    [...container.querySelectorAll<HTMLElement>(".v2-agent-demo")].filter(
      (demo) => demo.dataset.running === "true",
    );
  expect(runningDemos()).toHaveLength(1);
  expect(runningDemos()[0]).toHaveClass("v2-agent-demo--vision");
  fireEvent.click(screen.getByRole("tab", { name: /Áudio e contexto/ }));
  expect(runningDemos()).toHaveLength(1);
  expect(runningDemos()[0]).toHaveClass("v2-agent-demo--audio");
  hidden.mockReturnValue(true);
  fireEvent(document, new Event("visibilitychange"));
  expect(runningDemos()).toHaveLength(0);
  hidden.mockReturnValue(false);
  fireEvent(document, new Event("visibilitychange"));
  expect(runningDemos()).toHaveLength(1);
  expect(runningDemos()[0]).toHaveClass("v2-agent-demo--audio");
});

it("suspends the cycle offscreen and starts a fresh interval when the section returns", () => {
  vi.useFakeTimers();
  let setVisible: (visible: boolean) => void = () => {};
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(private callback: IntersectionObserverCallback) {}
      observe(target: Element) {
        setVisible = (visible) =>
          this.callback(
            [{ isIntersecting: visible, target } as IntersectionObserverEntry],
            this as unknown as IntersectionObserver,
          );
        setVisible(true);
      }
      disconnect() {}
    },
  );
  render(<AgentTeam />);
  const vision = screen.getByRole("tab", { name: /Visão computacional/ });
  const emg = screen.getByRole("tab", { name: /Sinais musculares/ });
  act(() => vi.advanceTimersByTime(5000));
  expect(emg).toHaveAttribute("aria-selected", "true");
  act(() => setVisible(false));
  fireEvent.click(vision);
  act(() => vi.advanceTimersByTime(15000));
  expect(vision).toHaveAttribute("aria-selected", "true");
  act(() => setVisible(true));
  act(() => vi.advanceTimersByTime(4999));
  expect(vision).toHaveAttribute("aria-selected", "true");
  act(() => vi.advanceTimersByTime(1));
  expect(emg).toHaveAttribute("aria-selected", "true");
});

it("keeps reduced-motion users in control and exposes only the final card after rapid selections", () => {
  vi.useFakeTimers();
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query) =>
      ({
        matches: true,
        media: query,
        onchange: null,
        addEventListener() {},
        removeEventListener() {},
        addListener() {},
        removeListener() {},
        dispatchEvent() {
          return true;
        },
      }) as MediaQueryList,
  );
  render(<AgentTeam />);
  const vision = screen.getByRole("tab", { name: /Visão computacional/ });
  const emg = screen.getByRole("tab", { name: /Sinais musculares/ });
  const audio = screen.getByRole("tab", { name: /Áudio e contexto/ });
  act(() => vi.advanceTimersByTime(15000));
  expect(vision).toHaveAttribute("aria-selected", "true");
  fireEvent.click(emg);
  fireEvent.click(vision);
  fireEvent.click(audio);
  expect(audio).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tabpanel")).toHaveAttribute(
    "aria-labelledby",
    audio.id,
  );
  expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(1);
  expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent(
    "Toda conversa tem um contexto.",
  );
});

it("selects hero portraits on click and swaps the identity only after its exit animation", async () => {
  vi.useFakeTimers();
  render(<Hero />);
  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  const lia = screen.getByRole("button", { name: /Conhecer Lia/ });
  const caio = screen.getByRole("button", { name: /Conhecer Caio/ });
  const ravi = screen.getByRole("button", { name: /Conhecer Ravi/ });
  expect(lia).toHaveAttribute("aria-pressed", "true");
  fireEvent.mouseEnter(caio);
  expect(lia).toHaveAttribute("aria-pressed", "true");
  await user.click(caio);
  expect(caio).toHaveAttribute("aria-pressed", "true");
  expect(lia).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByText("Lia")).toBeInTheDocument();
  act(() => vi.advanceTimersByTime(349));
  expect(screen.queryByText("Caio")).not.toBeInTheDocument();
  act(() => vi.advanceTimersByTime(1));
  expect(screen.getByText("Caio")).toBeVisible();
  act(() => vi.advanceTimersByTime(300));
  ravi.focus();
  await user.keyboard("{Enter}");
  expect(ravi).toHaveAttribute("aria-pressed", "true");
  act(() => vi.advanceTimersByTime(350));
  expect(screen.getByText("Ravi")).toBeVisible();
});

it("advances hero portraits when each five-second bar ends, after the identity has returned", () => {
  vi.useFakeTimers();
  render(<Hero />);
  const lia = screen.getByRole("button", { name: /Conhecer Lia/ });
  const caio = screen.getByRole("button", { name: /Conhecer Caio/ });
  const ravi = screen.getByRole("button", { name: /Conhecer Ravi/ });
  act(() => vi.advanceTimersByTime(4999));
  expect(lia).toHaveAttribute("aria-pressed", "true");
  act(() => vi.advanceTimersByTime(1));
  expect(ravi).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText("Lia")).toBeInTheDocument();
  act(() => vi.advanceTimersByTime(350));
  expect(screen.getByText("Ravi")).toBeInTheDocument();
  act(() => vi.advanceTimersByTime(4000));
  fireEvent.click(ravi);
  act(() => vi.advanceTimersByTime(999));
  expect(ravi).toHaveAttribute("aria-pressed", "true");
  act(() => vi.advanceTimersByTime(1));
  expect(caio).toHaveAttribute("aria-pressed", "true");
});

it("advances from the identity badge and ignores portrait clicks during the position swap", () => {
  vi.useFakeTimers();
  render(<Hero />);
  const caio = screen.getByRole("button", { name: /Conhecer Caio/ });
  const ravi = screen.getByRole("button", { name: /Conhecer Ravi/ });
  fireEvent.click(screen.getByRole("button", { name: /Próximo agente/ }));
  expect(ravi).toHaveAttribute("aria-pressed", "true");
  act(() => vi.advanceTimersByTime(100));
  fireEvent.click(caio);
  expect(ravi).toHaveAttribute("aria-pressed", "true");
  act(() => vi.advanceTimersByTime(550));
  fireEvent.click(caio);
  expect(caio).toHaveAttribute("aria-pressed", "true");
  act(() => vi.advanceTimersByTime(350));
  expect(screen.getByText("Caio")).toBeInTheDocument();
});
