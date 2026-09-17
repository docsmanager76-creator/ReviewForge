import { z } from "zod";

/**
 * TIMELINE_SCHEMA_VERSION follows semver-ish "major.minor". Bump the major version whenever a
 * field is removed or its meaning changes; bump the minor version for additive, backward
 * compatible fields. The Remotion renderer and the Python timeline builder both check this
 * value and refuse to run against a Timeline JSON with an unsupported major version.
 */
export const TIMELINE_SCHEMA_VERSION = "1.0";

const shotTypeEnum = z.enum([
  "hero",
  "close_up",
  "side_profile",
  "action_demo",
  "feature_shot",
  "specification_shot",
  "accessory_shot",
  "lifestyle_context",
]);

const motionPresetEnum = z.enum([
  "slow_push_in",
  "slow_pull_out",
  "pan_left_to_right",
  "pan_right_to_left",
  "subtle_parallax",
  "controlled_scale",
]);

const contentTypeEnum = z.enum([
  "intro",
  "feature",
  "spec",
  "comparison",
  "opinion",
  "cta",
  "outro",
  "transition_marker",
]);

const preferredMediaTypeEnum = z.enum(["image", "video_clip", "graphic", "b_roll"]);

const assetTypeEnum = z.enum(["image", "video"]);

const assetSourceEnum = z.enum(["local", "stock", "web_search"]);

const graphicsTemplateEnum = z.enum([
  "feature_lower_third",
  "cta_lower_third",
  "product_intro",
  "spec_card",
]);

const transitionTemplateEnum = z.enum(["shape_transition", "cut", "cross_dissolve"]);

const transitionTriggerEnum = z.enum(["new_product_section", "manual"]);

export const FileReferenceSchema = z.object({
  source: z.enum(["local_path", "native_picker", "desktop_wrapper"]),
  absolutePath: z.string().min(1),
  originalValue: z.string().optional(),
  displayName: z.string().optional(),
});

export const ProductSchema = z.object({
  name: z.string().min(1),
  brand: z.string().optional(),
  model: z.string().optional(),
  url: z.string().url().optional(),
  additionalUrls: z.array(z.string().url()).default([]),
});

export const ProjectSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  product: ProductSchema,
  createdAt: z.string(),
});

export const VisualIntentSchema = z.object({
  shotType: shotTypeEnum,
  description: z.string().min(1),
  motionPreset: motionPresetEnum.optional(),
});

export const GraphicsRequirementSchema = z.object({
  template: graphicsTemplateEnum,
  fields: z.record(z.string()),
});

export const TransitionRequirementSchema = z.object({
  template: transitionTemplateEnum,
  triggeredBy: transitionTriggerEnum,
});

export const SentenceSchema = z.object({
  id: z.string().min(1),
  index: z.number().int().nonnegative(),
  text: z.string().min(1),
  startTime: z.number().nonnegative(),
  endTime: z.number().nonnegative(),
  contentType: contentTypeEnum,
  topic: z.string().min(1),
  productSection: z.string().optional(),
  visualIntent: VisualIntentSchema,
  preferredMediaType: preferredMediaTypeEnum,
  fallbackMediaType: preferredMediaTypeEnum,
  graphicsRequirement: GraphicsRequirementSchema.optional(),
  transitionRequirement: TransitionRequirementSchema.optional(),
});

export const AssetUsageSchema = z.object({
  sceneId: z.string().min(1),
  usedAt: z.string(),
});

export const AssetSchema = z.object({
  id: z.string().min(1),
  product: z.string().min(1),
  type: assetTypeEnum,
  source: assetSourceEnum,
  filePath: z.string().min(1),
  description: z.string().default(""),
  tags: z.array(z.string()).default([]),
  visualCategory: shotTypeEnum,
  quality: z.number().min(0).max(1).default(0.5),
  durationSeconds: z.number().nonnegative().optional(),
  usageHistory: z.array(AssetUsageSchema).default([]),
});

export const SceneVisualSchema = z.object({
  type: z.enum(["image", "video_clip"]),
  assetId: z.string().min(1),
  filePath: z.string().min(1),
  motionPreset: motionPresetEnum.optional(),
  trimStart: z.number().nonnegative().optional(),
  trimEnd: z.number().nonnegative().optional(),
});

export const SceneGraphicSchema = z.object({
  template: graphicsTemplateEnum,
  fields: z.record(z.string()),
  startTime: z.number().nonnegative(),
  endTime: z.number().nonnegative(),
});

export const SceneTransitionSchema = z.object({
  template: transitionTemplateEnum,
  duration: z.number().positive(),
});

export const SceneSchema = z.object({
  id: z.string().min(1),
  sentenceId: z.string().min(1),
  startTime: z.number().nonnegative(),
  endTime: z.number().nonnegative(),
  visual: SceneVisualSchema,
  graphics: z.array(SceneGraphicSchema).default([]),
  transitionOut: SceneTransitionSchema.optional(),
});

export const TimelineSchema = z.object({
  version: z.literal(TIMELINE_SCHEMA_VERSION),
  project: z.object({
    id: z.string().min(1),
    title: z.string().min(1),
    product: z.string().min(1),
    fps: z.number().int().positive().default(30),
    resolution: z.object({
      width: z.literal(1920),
      height: z.literal(1080),
    }),
  }),
  audio: z.object({
    voiceoverPath: z.string().min(1),
    musicPath: z.string().optional(),
  }),
  scenes: z.array(SceneSchema).min(1),
  globalGraphics: z
    .object({
      productIntro: SceneGraphicSchema.optional(),
    })
    .default({}),
});

export type FileReference = z.infer<typeof FileReferenceSchema>;
export type Product = z.infer<typeof ProductSchema>;
export type Project = z.infer<typeof ProjectSchema>;
export type VisualIntent = z.infer<typeof VisualIntentSchema>;
export type GraphicsRequirement = z.infer<typeof GraphicsRequirementSchema>;
export type TransitionRequirement = z.infer<typeof TransitionRequirementSchema>;
export type Sentence = z.infer<typeof SentenceSchema>;
export type Asset = z.infer<typeof AssetSchema>;
export type Scene = z.infer<typeof SceneSchema>;
export type Timeline = z.infer<typeof TimelineSchema>;
