import React from "react";
import type { SceneGraphicSchema } from "@reviewforge/timeline-schema";
import type { z } from "zod";

type SceneGraphic = z.infer<typeof SceneGraphicSchema>;

/**
 * Template-based graphic. The renderer only ever fills in `fields` from the timeline JSON —
 * it never invents copy or layout. New templates are added here, keyed by name, not improvised
 * per-scene.
 */
export function GraphicOverlay({ graphic }: { graphic: SceneGraphic }) {
  const { template, fields } = graphic;

  if (template === "cta_lower_third") {
    return (
      <div style={lowerThirdStyle("#ff5b5b")}>
        <strong>{fields.title ?? "Link in the description"}</strong>
        {fields.subtitle && <div style={{ fontSize: 22, opacity: 0.85 }}>{fields.subtitle}</div>}
      </div>
    );
  }

  if (template === "feature_lower_third") {
    return (
      <div style={lowerThirdStyle("#5b8cff")}>
        <strong>{fields.title ?? ""}</strong>
        {fields.subtitle && <div style={{ fontSize: 22, opacity: 0.85 }}>{fields.subtitle}</div>}
      </div>
    );
  }

  if (template === "spec_card") {
    return (
      <div style={{ ...lowerThirdStyle("#2c2f36"), bottom: 220 }}>
        <strong>{fields.label ?? ""}</strong>
        <div style={{ fontSize: 28 }}>{fields.value ?? ""}</div>
      </div>
    );
  }

  if (template === "product_intro") {
    return (
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          background: "rgba(11,13,16,0.85)",
        }}
      >
        <h1 style={{ color: "white", fontSize: 64 }}>{fields.productName ?? ""}</h1>
        {fields.brand && <p style={{ color: "#9aa4b2", fontSize: 28 }}>{fields.brand}</p>}
      </div>
    );
  }

  return null;
}

function lowerThirdStyle(accent: string): React.CSSProperties {
  return {
    position: "absolute",
    left: 80,
    bottom: 120,
    padding: "16px 28px",
    background: "rgba(10,10,12,0.82)",
    borderLeft: `6px solid ${accent}`,
    color: "white",
    fontFamily: "sans-serif",
    fontSize: 34,
    borderRadius: 6,
    maxWidth: 900,
  };
}
