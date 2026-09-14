import type { JSX } from "react";
import type { CaptureLayout } from "../lib/captureLayout.js";

type DraftRegionProps = {
  window: NonNullable<CaptureLayout["draftWindow"]>;
};

export default function DraftRegion(_props: DraftRegionProps): JSX.Element {
  throw new Error("not implemented");
}
