import { render } from "ink-testing-library";
import { describe, expect, it } from "vitest";
import SourceViewport from "../src/components/SourceViewport";

const SAMPLE_LINES = ["alpha", "beta", "gamma", "delta", "epsilon"];

describe("SourceViewport", () => {
  it("renders only the slice from offset through offset plus height", () => {
    const { lastFrame } = render(
      <SourceViewport lines={SAMPLE_LINES} offset={1} height={2} />,
    );

    const frame = lastFrame() ?? "";
    expect(frame).toContain("beta");
    expect(frame).toContain("gamma");
    expect(frame).not.toContain("alpha");
    expect(frame).not.toContain("delta");
    expect(frame).not.toContain("epsilon");
  });

  it('shows a "more above" marker when offset is greater than zero', () => {
    const { lastFrame } = render(
      <SourceViewport lines={SAMPLE_LINES} offset={2} height={2} />,
    );

    expect(lastFrame()).toMatch(/more above/i);
  });

  it('omits the "more above" marker when offset is zero', () => {
    const { lastFrame } = render(
      <SourceViewport lines={SAMPLE_LINES} offset={0} height={2} />,
    );

    expect(lastFrame()).not.toMatch(/more above/i);
  });

  it('shows a "more below" marker when lines remain below the window', () => {
    const { lastFrame } = render(
      <SourceViewport lines={SAMPLE_LINES} offset={0} height={2} />,
    );

    expect(lastFrame()).toMatch(/more below/i);
  });

  it('omits the "more below" marker when the window includes the last line', () => {
    const { lastFrame } = render(
      <SourceViewport lines={SAMPLE_LINES} offset={3} height={2} />,
    );

    const frame = lastFrame() ?? "";
    expect(frame).toContain("epsilon");
    expect(frame).not.toMatch(/more below/i);
  });
});
