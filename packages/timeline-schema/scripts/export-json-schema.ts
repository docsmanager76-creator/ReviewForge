/**
 * Exports the TimelineSchema (and Project/Asset schemas) to plain JSON Schema so the Python
 * backend can validate timeline.json without re-implementing the schema. Run via
 * `npm run export-json-schema`. Output is checked into packages/timeline-schema/dist/ and read
 * by apps/api at startup.
 */
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { z } from "zod";
import { TimelineSchema, ProjectSchema, AssetSchema, TIMELINE_SCHEMA_VERSION } from "../src/schema";

const outDir = join(__dirname, "..", "dist");
mkdirSync(outDir, { recursive: true });

const schemas: Record<string, unknown> = {
  timeline: z.toJSONSchema(TimelineSchema),
  project: z.toJSONSchema(ProjectSchema),
  asset: z.toJSONSchema(AssetSchema),
};

for (const [name, schema] of Object.entries(schemas)) {
  writeFileSync(join(outDir, `${name}.schema.json`), JSON.stringify(schema, null, 2));
}

writeFileSync(join(outDir, "VERSION"), TIMELINE_SCHEMA_VERSION);

console.log(`Exported JSON Schemas (version ${TIMELINE_SCHEMA_VERSION}) to ${outDir}`);
