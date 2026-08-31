import { render } from "ink-testing-library";
import { describe, expect, it } from "vitest";
import App from "../src/app";

describe("App", () => {
  it("renders the capture screen input prompt", () => {
    const { lastFrame } = render(<App />);

    expect(lastFrame()).toContain("Weles");
  });

  it("renders a non-empty bootstrap frame", () => {
    const { lastFrame } = render(<App />);

    expect(lastFrame()).toBeTruthy();
  });
});
