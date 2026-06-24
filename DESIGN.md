# DESIGN.md — Urban Air Quality Forecasting

The brief: **playful, bold, and intriguing enough that a stranger wants to click around** — a playground, not a report. And it must look *designed by a person with taste*, not generated. This file is the visual + interaction contract. The Anti-Slop Checklist below is enforced by `rules.md`.

---

## North star

The city is breathing. The whole interface should feel like a living atmosphere — air that goes from clean to hazy and back. The user is a curious explorer poking at a living system, watching it react. Drama is allowed; dishonesty about the data is not.

## Visual identity (specific to this project — do not reuse elsewhere)

- **Concept:** "Atmosphere." A clean-air-to-smog gradient is the signature motif, used for backgrounds, transitions, and the AQI scale.
- **Palette:** Build a custom AQI-aware scale (not the default EPA primary colors, but a refined, color-blind-safe interpretation). Anchor neutrals in a cool charcoal "night sky," with luminous accent for "clean." Hazard tones (amber → ember → violet-red) escalate with AQI. Pair every color with a non-color cue (shape, label, value) — never color alone.
- **Typography:** One characterful display face for big numbers and headers (a grotesque or a distinctive geometric sans — e.g. Space Grotesk, Clash Display, or similar), one highly legible face for data/labels (Inter, IBM Plex Sans). Big, confident AQI numerals are a hero element.
- **Texture:** Subtle grain/noise and soft atmospheric blur to avoid the flat, sterile "template" look. Use sparingly.

## Anti-Slop Checklist (mandatory — a PR fails if any are true)

- ❌ No default-template hero: centered headline + subtitle + two pill buttons over a purple/indigo diagonal gradient.
- ❌ No untouched component-library defaults (no out-of-the-box shadcn/MUI cards as the actual design — restyle or don't use).
- ❌ No emoji used as iconography or data markers. Use a real icon set (Lucide, Phosphor) or custom SVG.
- ❌ No generic stock "data/AI" imagery, glowing brains, or circuit-board motifs.
- ❌ No three-equal-cards-in-a-row as the primary layout. Use an intentional, asymmetric grid.
- ❌ No lorem ipsum and no fake numbers in the shipped UI — bind to the real API.
- ✅ A distinctive, memorable signature interaction (here: the breathing/horizon-scrub recolor) that no template would ship.
- ✅ Deliberate type scale, spacing rhythm, and one surprising-but-tasteful detail per screen.

## Interactivity Spec (this is the product — not decoration)

Every one of these responds to user input in real time:

1. **Living map (MapLibre GL).** Stations are markers that pulse subtly with current AQI. Click → focus + detail panel. Hover → quick read. Pan/zoom is smooth; markers cluster at low zoom.
2. **Horizon scrubber.** A draggable timeline (now → +24h). As the user drags, the map markers and the forecast chart recolor and re-tween live. This is the signature moment — make it feel buttery.
3. **Pollutant switch (PM₂.₅ / O₃ / NO₂).** Animated crossfade/morph between scales, not a reload. State persists in the URL so a view is shareable.
4. **Play button.** Auto-animates the next 24h; the city visibly hazes and clears. Pause/scrub at any point.
5. **Station compare.** Pin two stations and watch their forecasts race side by side.
6. **Honesty overlays that stay interactive.** Confidence band can be toggled; hovering a point shows value, CI, freshness, and whether it's interpolated.

## Motion budget

- Use **Framer Motion** for component/state transitions and **spring** physics for the scrubber and marker tweens (springs feel alive; linear eases feel templated).
- Target 60fps while scrubbing. Animate transform/opacity only; never animate layout-thrashing properties.
- Every animation has a `prefers-reduced-motion` fallback that snaps instead of tweens. Motion must never hide data or delay interaction.

## Design & visualization toolkit ("design skills" to use)

- **Charts:** prefer **visx** (composable, fully custom — best for escaping the default-chart look) or **Recharts** if speed matters; restyle aggressively. Avoid shipping any chart with library-default colors/tooltips.
- **Map:** MapLibre GL JS (open, no token) with a custom dark style.
- **Motion:** Framer Motion; consider a light particle/atmosphere layer (tsParticles or a hand-rolled canvas) used tastefully.
- **Styling:** Tailwind with a **custom design-token theme** (colors, type scale, spacing) — do not ship Tailwind's raw default palette as the brand.
- **Iconography:** Lucide or Phosphor; custom SVG for the AQI gauge.
- **Color tooling:** verify the AQI scale with a color-blindness simulator; use a perceptually-uniform scale (e.g. via d3-scale-chromatic / d3-interpolate) so steps read evenly.
- If working inside Cowork, the `data:data-visualization`, `data:create-viz`, and `data:build-dashboard` skills encode useful chart-selection and dashboard-layout principles — apply their guidance, but the **final styling must clear the Anti-Slop Checklist**, not look like a generated dashboard.

## Layout & accessibility

- Asymmetric, intentional layout: a dominant map canvas, a docked forecast rail, a slim control bar. Not a uniform card grid.
- Keyboard-navigable everything; visible focus rings; the map has an equivalent data table fallback.
- Color-blind-safe AQI encoding (color **plus** shape/label) per `rules.md` G4.
- Mobile: the map stays the hero; controls collapse into a thumb-reachable bottom sheet that is still fully interactive.
