export type ShotType =
  | "hero"
  | "close_up"
  | "side_profile"
  | "action_demo"
  | "feature_shot"
  | "specification_shot"
  | "accessory_shot"
  | "lifestyle_context";

export type MotionPresetName =
  | "slow_push_in"
  | "slow_pull_out"
  | "pan_left_to_right"
  | "pan_right_to_left"
  | "subtle_parallax"
  | "controlled_scale";

export type ContentType =
  | "intro"
  | "feature"
  | "spec"
  | "comparison"
  | "opinion"
  | "cta"
  | "outro"
  | "transition_marker";

export type PreferredMediaType = "image" | "video_clip" | "graphic" | "b_roll";

export type AssetType = "image" | "video";

export type AssetSource = "local" | "stock" | "web_search";

export type GraphicsTemplate =
  | "feature_lower_third"
  | "cta_lower_third"
  | "product_intro"
  | "spec_card";

export type TransitionTemplate = "shape_transition" | "cut" | "cross_dissolve";

export type TransitionTrigger = "new_product_section" | "manual";

export type JobStatus = "pending" | "running" | "succeeded" | "failed";

export type JobType =
  | "transcribe"
  | "analyze_sentences"
  | "plan_visuals"
  | "rank_assets"
  | "build_timeline"
  | "render";
