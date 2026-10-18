# Local LLM Studio identity

Studio is an open-source workspace for people exploring models through a local model server.

**Brand line:** Your models. Your workspace.

**Symbol:** An amber core inside a ring, with a short connection extending toward the outside. The core represents the model; the ring represents the workspace the user controls. Keep the symbol upright and leave at least one core-width of clear space around it.

**Palette:** Slate `#293c44`, deep slate `#203139`, paper `#f3f6f7`, white `#ffffff`, amber `#efb544`, and muted slate `#61747d`. Amber is a highlight and control background; use deep slate text on amber.

**Typography:** Avenir Next with Segoe UI and sans-serif fallbacks for headings and body copy. Use compact heading tracking and generous body line height. Use SFMono-Regular, Cascadia Mono, or system monospace for model names and technical data. All fonts use local system fallbacks; no external font requests.

**Voice:** Plain, helpful, and specific. Name the action, explain the next step, and avoid claiming that every model runs locally: a local runtime can expose cloud models.

## Assets

Files live in `web/public/brand/`:

- `studio-symbol.svg`: scalable symbol, also used as `web/public/favicon.svg`.
- `studio-wordmark.svg`: symbol with the Studio wordmark for light backgrounds; uses system font fallbacks.
- `apple-touch-icon.png`: 180 × 180.
- `icon-192.png` and `icon-512.png`: install icons referenced by `site.webmanifest`.
- `og-image.png`: 1200 × 630 social preview.

## Public sharing metadata

The app includes Open Graph and Twitter large-image metadata in the initial HTML. For a publicly hosted project page, set `VITE_PUBLIC_SITE_URL=https://your-real-domain` when building. This adds a canonical URL and `og:url` and makes social image URLs absolute. The setting expects an origin; paths are ignored. Do not set it to a guessed domain.

Without the setting, local assets still work and canonical URL tags are omitted. Social crawlers cannot reach a loopback server, so external previews require a public host serving the built HTML and image. This does not make Studio's private backend public.


## Generated image set

Created with the built-in image generation tool. Source PNGs are retained alongside optimized web exports in `web/public/brand/`.

- `studio-logo-generated.png`: transparent source logo. `studio-logo.webp` is the 256 px UI export.
- `workspace-background.png`: source orbital background. `workspace-background.webp` is the optimized background used in Setup and Chat.
- `social-card-generated.png`: generated social artwork. `og-image-v2.png` is the 1200 × 630 Open Graph export.
- `favicon-32-v2.png`, `apple-touch-icon-v2.png`, `icon-192-v2.png`, `icon-512-v2.png`: exports of the generated logo.

Earlier SVG and PNG assets are retained as previous versions. The interface, manifest, and sharing metadata reference the new image set.

### Final generation prompts

**Logo**

Use case: logo-brand. Generate one production logo symbol for Local LLM Studio, an open-source local AI workspace. Transparent background. A precise minimal amber circular core inside a single open orbital ring with a short diagonal terminal at upper right, set within a deep slate rounded-square tile. Palette slate #293c44 and amber #efb544. Flat vector-like geometry, exceptionally crisp, no gradients, no shadows, no text, no mockup, no extra symbols. Centered square composition, tile occupies 85% of canvas. Must remain recognizable at favicon size. Output a single logo image.

**Background**

Use case: stylized-concept. Website background artwork for Local LLM Studio, a calm private AI workspace. Wide landscape 3:2 composition. Soft paper-white #f3f6f7 background with a sophisticated sculptural arrangement of concentric orbital arcs and small rounded slate #293c44 modules with restrained amber #efb544 cores, all concentrated in the rightmost third. Left two thirds almost empty with faint soft relief only, ideal for overlaid interface text. Precision industrial product illustration, matte ceramic materials, soft daylight, very low contrast, subtle depth. No text, no letters, no numbers, no logos, no circuitry, no glowing neon. Elegant quiet architectural still life, not a futuristic sci-fi scene.

**Social card** (references: generated logo and background)

Create a polished wide 1.91:1 social sharing card for Local LLM Studio using these two reference assets. First is the brand logo, second is the background style. Place the logo small in the upper left with the exact title 'Local LLM Studio'. Large perfectly legible dark slate headline on left: 'Your models.' on one line and 'Your workspace.' below. Smaller line below: 'Chat, vision, and benchmarks.' Preserve empty pale background beneath all text and orbital illustration concentrated on right. Slate #293c44, amber #efb544, paper #f3f6f7. Professional restrained typography, ample padding all edges, no additional copy, no UI mockup. Use the logo identity faithfully.


## Professional material refinement

The current UI logo is `studio-logo-professional.webp`, exported from `studio-logo-professional.png`. The favicon and installed app icons use the `-v3.png` files. Earlier assets remain available.

Generated with the built-in image tool using `studio-logo-generated.png` as the edit reference and this prompt:

Refine this exact Local LLM Studio logo into a realistic, exceptionally professional premium industrial emblem. Preserve its identity: centered circular core, open orbital ring with short diagonal terminal at upper right, dark slate rounded square. Render as a precision-machined physical app icon: matte dark slate anodized aluminum tile (#293c44), subtly raised satin brushed champagne-amber metal ring and circular core, finely chamfered edges, very shallow realistic depth, restrained studio light from upper left. Front-facing orthographic, perfectly centered and symmetrical, no perspective tilt. The ring has uniform thickness and a clean intentional gap, mechanically precise curves. Sophisticated understated product photography realism, not toy-like, not glossy plastic, not exaggerated 3D, no glow, no dramatic reflections. Strong small-size legibility. No text or additional decoration. Tile fills about 88 percent of square canvas. Truly transparent background outside tile; preserve alpha. Single production-ready logo only.
