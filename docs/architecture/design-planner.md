# Design Planner

## Responsibility

The Design Planner converts content intent into page-level design decisions. It
sits after slide content planning and before geometry resolution.

```text
brief + outline + slide-plan
              |
              v
       Design Planner
       |      |      |
       |      |      +-- base design rules
       |      +--------- layout selection rules
       +---------------- page type rules
              |
              v
        design-plan.json
```

The planner does not render slides, create coordinates, rewrite content, or
invent assets. Phase 3 resolves its decisions against executable layouts.

## Decision Order

1. Define the slide's narrative job, primary claim, connection to adjacent
   slides, and pacing beat.
2. Decide the dominant read, reading order, emphasis levels, and subordinate detail.
3. Select a visual form that carries the claim and define any image's role and crop intent.
4. Measure content items and approximate character density; allocate whitespace accordingly.
5. Choose a composition silhouette, grouping logic, balance, and contrast strategy.
6. Score compatible layouts by those decisions, capacity, and preserved v1 intent.
7. Add asset requirements and quality constraints.
8. Check deck-level rhythm and use a compatible alternate where repetition would flatten the story.

The reasoning model and benchmark are documented in
`design-planner-benchmark.md`.

## Knowledge Base

- `page-type-rules.v1.json`: communication job, visual forms, density, and required notes.
- `layout-selection-rules.v1.json`: layout compatibility, capacity, assets, and fallbacks.
- `base-design-rules.v1.json`: typography budgets, fit priority, deck rhythm, and forbidden patterns.

The rules are data, not planner branches. Phase 3 may replace provisional layout
metadata with the executable layout registry without changing the design-plan
contract.

## LLM Boundary

`agent/skills/design-planner/prompt.md` defines the LLM role. LLM output must
conform to the same schema as the deterministic planner. The deterministic
implementation is the fallback, regression oracle, and safe baseline.
