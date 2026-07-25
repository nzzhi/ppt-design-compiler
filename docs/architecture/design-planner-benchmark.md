# Design Planner Benchmark and Upgrade Rationale

## Scope

This review synthesizes the previously recorded findings from
`academic-pptx-skill`, `PPTAgent`, `Presenton`, `Akxan ppt-agent-skill`,
`guizang-ppt-skill`, and `appautomaton/presentation`. It adopts design
principles, not third-party code, prompts, templates, or assets.

## Why the stronger skills produce better work

Their advantage is not a larger layout menu. They make several coupled design
decisions before rendering:

1. They define the audience outcome and narrative beat before composing a page.
2. They give each slide one dominant read and turn titles into claims.
3. They fit the amount and relationship of content to the composition, rather
   than pouring text into a chosen container.
4. They treat images as evidence or framing devices with an intended crop,
   subject position, and negative space.
5. They manage deck rhythm across slides, varying silhouettes at story beats
   while keeping typography, grid, and visual treatment coherent.
6. They encode professional template behavior: capacity, image slots,
   typography budgets, fallbacks, and repeat limits.

These choices resemble human design practice: establish the point, sketch the
dominant mass, decide the reading path, edit content to fit, then choose or
adapt a known composition.

## Capabilities missing from the previous planner

| Design concern | Previous behavior | Missing capability |
| --- | --- | --- |
| Visual hierarchy | Generic note about scale and whitespace | Dominant element, reading order, emphasis levels, deliberate de-emphasis |
| Page narrative | Page type inferred independently | Entry logic, exit logic, pacing, and deck-level arc |
| Density | Character and item thresholds | Whitespace policy and a composition response tied to density |
| Images | Asset type and aspect ratio | Communication role, focal position, crop intent, negative space, treatment, fallback |
| Layout combinations | Single winning layout ID | Composition silhouette first, ranked alternatives, variation rationale |
| Professional templates | Small layout catalog | Reusable grammar: hierarchy, grid behavior, image discipline, capacity and rhythm policies |
| Human habits | Warn after three repeated families | Design the eye path and proactively select a viable alternate when available |

## Capabilities added to ppt-agent

The Design Planner now emits five explicit decision layers:

- `narrative`: what the page must do and how it connects to adjacent pages.
- `hierarchy`: what the audience sees first, next, and last.
- `composition`: silhouette, balance, reading pattern, whitespace, grouping,
  contrast, and variation rationale.
- `image_strategy`: whether an image is justified and how it must be framed.
- `layout`: the registered implementation choice after the above decisions.

The deck direction now records the communication job, narrative arc, hierarchy,
image, layout, density, and rhythm strategies. The renderer remains unchanged;
these fields are planning inputs for the future Layout Engine and richer QA.

## Design principles retained

- One primary claim and one dominant exhibit per slide.
- Lower density with higher-value content.
- Flat canvas composition instead of default card grids.
- Images must carry information; diagrams must improve comprehension.
- Shorten, change layout, or split before shrinking below the type budget.
- Layout variety follows narrative function, not decoration.

