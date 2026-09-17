import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { TimelineSchema, type Timeline, type Scene } from "@reviewforge/timeline-schema";
import { motionStyle } from "./motionPresets";
import { GraphicOverlay } from "./LowerThird";

export interface TimelineCompositionProps {
  timeline: Timeline;
}

const SHOT_COLORS: Record<string, string> = {
  hero: "#5b8cff",
  close_up: "#8c5bff",
  side_profile: "#ff8c5b",
  action_demo: "#ff5b8c",
  feature_shot: "#5bffb0",
  specification_shot: "#5bd0ff",
  accessory_shot: "#ffdd5b",
  lifestyle_context: "#a0a4ab",
};

/** Validates props at render time — this is the last line of defense before the deterministic
 * renderer runs; an invalid Timeline JSON must fail loudly here rather than render silently. */
export function validateTimelineProps(props: unknown): TimelineCompositionProps {
  const timeline = TimelineSchema.parse((props as any).timeline);
  return { timeline };
}

function SceneLayer({ scene, fps }: { scene: Scene; fps: number }) {
  const frame = useCurrentFrame();
  const durationInFrames = Math.max(1, Math.round((scene.endTime - scene.startTime) * fps));
  const color = SHOT_COLORS[scene.visual.assetId.length % 2 === 0 ? "hero" : "close_up"] ?? "#333";

  return (
    <AbsoluteFill style={{ background: "#0b0d10" }}>
      <AbsoluteFill
        style={{
          ...motionStyle(scene.visual.motionPreset, frame, durationInFrames),
          background: `linear-gradient(135deg, ${color}, #101318)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ color: "white", fontFamily: "sans-serif", textAlign: "center" }}>
          <div style={{ fontSize: 22, opacity: 0.7 }}>{scene.visual.type}</div>
          <div style={{ fontSize: 32, fontWeight: 600 }}>{scene.visual.assetId}</div>
        </div>
      </AbsoluteFill>
      {scene.graphics.map((graphic, i) => (
        <GraphicOverlay key={i} graphic={graphic} />
      ))}
    </AbsoluteFill>
  );
}

export function TimelineComposition({ timeline }: TimelineCompositionProps) {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill>
      {timeline.scenes.map((scene) => {
        const from = Math.round(scene.startTime * fps);
        const durationInFrames = Math.max(1, Math.round((scene.endTime - scene.startTime) * fps));
        return (
          <Sequence key={scene.id} from={from} durationInFrames={durationInFrames}>
            <SceneLayer scene={scene} fps={fps} />
          </Sequence>
        );
      })}
      {timeline.globalGraphics.productIntro && (
        <Sequence
          from={Math.round(timeline.globalGraphics.productIntro.startTime * fps)}
          durationInFrames={Math.max(
            1,
            Math.round(
              (timeline.globalGraphics.productIntro.endTime - timeline.globalGraphics.productIntro.startTime) * fps
            )
          )}
        >
          <GraphicOverlay graphic={timeline.globalGraphics.productIntro} />
        </Sequence>
      )}
    </AbsoluteFill>
  );
}
