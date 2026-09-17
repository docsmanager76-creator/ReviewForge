import { interpolate } from "remotion";
import type { MotionPresetName } from "@reviewforge/timeline-schema";

/**
 * Deterministic, reusable motion presets. Every preset is a pure function of (frame,
 * durationInFrames) so the same timeline JSON always renders identically — no randomness,
 * no AI involvement at render time.
 */
export function motionStyle(
  preset: MotionPresetName | undefined,
  frame: number,
  durationInFrames: number
): React.CSSProperties {
  const t = durationInFrames <= 1 ? 0 : frame / (durationInFrames - 1);

  switch (preset) {
    case "slow_push_in":
      return { transform: `scale(${interpolate(t, [0, 1], [1, 1.08])})` };
    case "slow_pull_out":
      return { transform: `scale(${interpolate(t, [0, 1], [1.08, 1])})` };
    case "pan_left_to_right":
      return { transform: `translateX(${interpolate(t, [0, 1], [-3, 3])}%) scale(1.06)` };
    case "pan_right_to_left":
      return { transform: `translateX(${interpolate(t, [0, 1], [3, -3])}%) scale(1.06)` };
    case "subtle_parallax":
      return { transform: `translateY(${interpolate(t, [0, 1], [-2, 2])}%) scale(1.05)` };
    case "controlled_scale":
      return { transform: `scale(${interpolate(t, [0, 0.5, 1], [1, 1.04, 1])})` };
    default:
      return {};
  }
}
