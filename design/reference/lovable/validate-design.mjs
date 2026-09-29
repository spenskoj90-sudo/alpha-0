// Checks that design registries stay consistent with the code. Run: node scripts/validate-design.mjs
import { readFileSync, existsSync } from "node:fs";

const errors = [];
const css = readFileSync("src/styles.css", "utf8");
const tokens = JSON.parse(readFileSync("design/tokens.json", "utf8"));
const assets = JSON.parse(readFileSync("design/assets.json", "utf8"));
const screens = JSON.parse(readFileSync("design/screens.json", "utf8"));

for (const [name, value] of Object.entries(tokens.color?.dark ?? {})) {
  if (value.startsWith("var(")) continue;
  if (!css.includes(`--${name}: ${value}`)) errors.push(`dark token --${name} differs from src/styles.css`);
}
for (const a of assets.assets) if (!existsSync(a.path)) errors.push(`missing asset ${a.path}`);
const ids = new Set();
for (const s of screens) {
  const id = s.id ?? s.name;
  if (ids.has(id)) errors.push(`duplicate screen ${id}`);
  ids.add(id);
}

if (errors.length) { console.error(errors.join("\n")); process.exit(1); }
console.log(`OK: ${Object.keys(tokens.color?.dark ?? {}).length} tokens, ${assets.assets.length} assets, ${screens.length} screens`);
