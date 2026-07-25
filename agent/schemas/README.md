# Schemas

The schema layer is the agent's memory contract. The rendered PowerPoint is the final artifact, but these JSON files make preview, repair, and targeted revision stable.

## Contract Versions

Version 1 contracts remain supported by the legacy renderer. They are not modified in place.

Version 2 contracts live in `v2/` and separate semantic planning from geometry:

- `v2/slide-plan.schema.json`: audience-facing semantic slide intent and typed content.
- `v2/design-system.schema.json`: semantic tokens and enforceable visual policies.
- `v2/design-plan.schema.json`: page-level design decisions without geometry.
- `v2/layout-registry.schema.json`: registered layout slots, capacity, and fit rules.
- `v2/render-plan.schema.json`: resolved geometry consumed by rendering and QA.

Use `agent.core.contracts` to resolve a contract by name and version. Use
`agent.core.compatibility.upgrade_slide_plan_v1` to adapt an existing v1 slide
plan in memory. The adapter does not rewrite project files.

The architecture and phased migration are documented in
`docs/architecture/v2-design-compiler.md`.
