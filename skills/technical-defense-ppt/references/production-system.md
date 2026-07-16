# Asset-first Production System

## Gate 0 — prepare all visual roles before page layout

Do not start from an outline alone. Build an asset packet and page-to-asset map first. Search supplied folders before requesting anything. If gaps remain, make one consolidated request or execute a targeted search/generation action.

| Role | Minimum prepared material | Typical sources |
| --- | --- | --- |
| cover / mission | wide hero + two support crops | system, lab, team, field, task frame |
| innovation | large material photo + two unequal details + comparison fact | hardware, wiring, sensor, log, before/after |
| mechanism | factual inputs/outputs + one anchor record | interface, code output, field frame, telemetry |
| planning / control | map/plot + field frame + criterion/result | route, map, video still, parameter/log |
| validation / video | primary 20–30 s clip + 2–4 labelled beats | edited clip and selected stills |
| outlook | contextual scene + verified-core evidence | source-cleared image, archive, generated editorial scene |
| finish layer | reusable material fragments | map grid, document crop, telemetry, macro detail, dark plate |

Use `asset-manifest-template.md`. Each asset records source/path, evidence role, claim it supports or does not support, page candidates, crop potential, visual grade, and ownership/licence status.

## Gate 1 — page-to-asset map

For every planned page select:

1. **Hero:** primary evidence or main visual explanation, normally 30–60% of visual weight.
2. **Support:** a different crop/material that adds context, comparison, scale, or proof.
3. **Finish:** one purposeful composition layer: caption rail, crop overlap, map grid, archival fragment, tonal field, measurement ticks, or transparent material background.

If any role is unavailable, resolve it before layout by selecting another packet asset, searching, generating a clearly non-evidentiary material, merging the page, or moving it to backup. Never fill the gap with generic shapes.

## Gate 2 — one-pass page lock

Before drawing, decide internally:

```text
spoken conclusion:
claim level and boundary:
hero asset + exact crop + visual share:
support asset + exact crop + visual share:
finish layer and purpose:
formal figure/table source:
paper field, deep plate, and signal-color roles:
adjacent-page differentiation:
speaker beat and time budget:
```

## Gate 3 — internal review, then one user-facing candidate

For each page: build → export → inspect full-resolution image → review against the rubric → rebuild internally until it passes. The user should see a polished candidate, not a wireframe or an unfinished “first pass.”

Reject internally if the page has unassigned empty paper, weak/cropped-too-small evidence, a missing hero/support/finish role, generic flow boxes, repeated adjacent visual treatment, or an unreadable speaking path.

## Sequential production

1. Asset packet, manifest, material board, and narrative/evidence map.
2. Calibrate with cover + hardest technical page + strongest material/innovation page; obtain direction approval only if no visual direction is already accepted.
3. Build in story order from the latest approved PPTX, inspecting each new page next to its predecessor.
4. Deliver only after 2–3 mutually coherent pages are inspected; retain three disposable previews.
5. At the end, replace placeholders, stage one main video, add notes/Q&A cues, and render the entire deck as a sequence.

## Visual finish contract

Premium technical slides are not blank reports with extra shapes. Each page is an authored visual scene around one conclusion.

| Item | Required decision |
| --- | --- |
| hero visual | exact photo/map/log/video frame or formal figure, crop, visual area |
| supporting material | different photo crop, close detail, archive fragment, context scene, or generated explanatory layer |
| finish layer | caption system, crop overlap, tonal field, measurement rail, technical texture, document veil, or controlled mask |
| image treatment | grade, saturation, contrast, opacity, edge/mask, caption |
| decoration role | orient / frame / pace / create depth — otherwise remove |
| anti-repetition | what changes from adjacent page family |

Except an intentional closing pause, a normal page needs a dominant proof anchor, a materially distinct support, an editorial finish layer, and a quiet title/conclusion field that frames information rather than replacing it. If the hero leaves a large pale field, first consider a controlled-opacity crop of relevant dark project material under text. It must add technical context, not imitate a generic background.

### Composition modes

| Mode | Best for | Ingredients |
| --- | --- | --- |
| documentary split | mission/context/application | wide scene, deliberate text space, real evidence inset |
| material dossier | hardware/innovation | large material photo, unequal details, comparison strip |
| technical atlas | map/planning/coordinate | large map plate, route/zone layer, field-frame inset, legend/measurement rail |
| proof topology | mechanism/control/communication | ownership lanes/arrows plus real record or sensor image |
| cinematic evidence stage | video/test | large still, 2–4 proof beats, restrained dark/tonal plate |
| editorial proposition | outlook/closing | oversized statement, contextual material, compact proof list |

Reject a page if it reads as a wireframe, a generic card grid, a pasted hero with no treatment, a single image plus text column, a set of pseudo-device shapes, or decoration made mainly of small brackets/chips/circles/bars. Richness must come from imagery, crop, type, formal figures, and purposeful material contrast.

## Topology / flow grammar

Choose a relation grammar before drawing. A flowchart must expose causality, ownership, branch conditions, feedback, or evidence — never merely list modules.

| Relation | Preferred grammar | Avoid |
| --- | --- | --- |
| sequential mission | route / decision spine | equal cards in a row |
| branch and guards | decision tree / state topology | labels floating without a branch |
| cross-system ownership | swim lanes / responsibility topology | one giant central controller box |
| data transformation | source → transform → output pipeline | generic architecture collage |
| planning constraints | map + annotated trajectory + constraint tree | algorithm boxes detached from a map |
| return/feedback | loop / state transition graph | arrows crossing unrelated nodes |

Give the primary path one reading direction and real arrowheads; use a secondary line style for feedback or return. Group by responsibility with lanes, whitespace, and alignment. Put conditions on their branches. Anchor at least one area in real evidence. Use signal color sparingly.

For trees, dependency graphs, state machines, and multi-lane ownership diagrams, use Graphviz, Matplotlib, SVG, or another programmatic figure source. Preserve source (`.py`/`.dot`), SVG, and PNG fallback. This yields stable alignment, true branches, and evidence provenance instead of manually piled PowerPoint boxes.

## Image search and provenance

Search for a visual role and composition, not “beautiful PPT images.” Include subject, camera/crop, palette, placement, and evidence boundary in the brief. Examples: `robotics wiring macro editorial negative space`, `technical map grid dark transparent background`, `emergency logistics aerial documentary wide low saturation`.

External imagery enriches atmosphere and background; it must never impersonate project proof. Record source/usage status, crop it for the page, and grade it into the local palette. Generated imagery is acceptable for scene setting or invisible mechanisms, never as fabricated test evidence.

## Review rubric

Score each page before preview. Anything below 80/100 or with a hard failure is rebuilt internally.

| Dimension | Points |
| --- | ---: |
| spoken claim & narrative role | 15 |
| evidence & provenance | 15 |
| claim boundary | 10 |
| hero composition | 15 |
| typography, grid, spacing | 10 |
| image integration & materiality | 10 |
| art direction & finish | 10 |
| diagram / flow quality | 8 |
| color/depth discipline | 4 |
| Q&A readiness & time | 3 |

Hard failures: unsupported deployment claim; controlled test presented as universal proof; innovation label without mechanism/material evidence; generic card-grid/pseudo-device/thick-arrow box flow; contextual image mistaken for project evidence; unknown asset rights in final deliverable; missing hero/support/finish; or unexplained adjacent-page duplication.

Revision order: correct claim → strengthen evidence → remove non-functional elements → rebuild reading path/figure grammar → improve crop/material/contrast/notes → re-render.
