import React from "react";
import { Composition } from "remotion";
import { TimelineComposition, validateTimelineProps } from "./TimelineComposition";
import sampleTimeline from "../sample/timeline.sample.json";

const FPS = 30;

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="TimelineComposition"
      component={TimelineComposition}
      durationInFrames={calculateDurationInFrames(sampleTimeline as any, FPS)}
      fps={FPS}
      width={1920}
      height={1080}
      defaultProps={{ timeline: sampleTimeline } as any}
      calculateMetadata={async ({ props }) => {
        const validated = validateTimelineProps(props);
        return {
          props: validated,
          durationInFrames: calculateDurationInFrames(validated.timeline, FPS),
          fps: validated.timeline.project.fps ?? FPS,
          width: validated.timeline.project.resolution.width,
          height: validated.timeline.project.resolution.height,
        };
      }}
    />
  );
};

function calculateDurationInFrames(timeline: { scenes: { endTime: number }[] }, fps: number): number {
  const maxEnd = Math.max(1, ...timeline.scenes.map((s) => s.endTime));
  return Math.max(1, Math.round(maxEnd * fps));
}
