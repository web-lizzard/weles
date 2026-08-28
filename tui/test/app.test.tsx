import { render } from "ink-testing-library";
import { describe, expect, it } from "vitest";
import App from "../src/app";

describe("App", () => {
  it('renders "Weles TUI — bootstrap OK" in the terminal', () => {
    const { lastFrame } = render(<App />);

    expect(lastFrame()).toContain("Weles TUI — bootstrap OK");
  });

  it("renders a non-empty bootstrap frame", () => {
    const { lastFrame } = render(<App />);

    expect(lastFrame()).toBeTruthy();
  });
});
