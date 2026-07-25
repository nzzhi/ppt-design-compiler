# Design Planner

The Design Planner converts a semantic or legacy slide plan into a separate
`design-plan.json`. It makes design decisions before the Layout Engine resolves
exact geometry: narrative pacing, visual hierarchy, composition, information
density, image framing, layout choice, and cross-slide rhythm.

Inputs:

- `slide-plan.json` using schema `1.0.0` or `2.0.0`
- page type, layout selection, and base design rules in `design-library/knowledge/`

Output:

- `design-plan.json` using `agent/schemas/v2/design-plan.schema.json`

The deterministic planner is the fallback and test oracle. An LLM Design
Planner may enrich the decisions using `prompt.md`, but must return the same
contract and obey the same knowledge rules.

```powershell
python agent/skills/design-planner/planner.py projects/<id>/plan/slide-plan.json projects/<id>/plan/design-plan.json
```

This skill does not render slides and does not modify the source slide plan.
