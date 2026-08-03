# PPT Agent Runtime

## Purpose

The runtime is the interaction layer around the existing planning and rendering
pipeline. It keeps user conversation, template discovery, optional skills,
revision targeting, and QA decisions outside individual renderers.

```text
request -> intake -> brief confirmation -> outline preview -> design / render
        -> QA -> targeted revision -> re-render
```

## Add a Template

1. Add a theme JSON file to `design-library/themes/`.
2. Add compatible layout records to `design-library/layouts/layout-registry.v2.json`.
3. Use the theme ID in an intake request, or let `TemplateCatalog` select it by use case.

No renderer or Agent runtime code needs to change for a theme-only addition.

## Add a Skill

Register a `Capability` with `PresentationAgent.skills`. A capability declares
the operations it supports and may provide a handler. The core Agent can then
use it for an isolated responsibility such as asset search, image generation,
data lookup, or a specialist page renderer.

```python
agent.skills.register(
    Capability("asset-search", "Find approved images", ("search",)),
    handler=search_assets,
)
```

An unregistered or unavailable skill does not block the main design pipeline.

## Current Scope

- Intake creates a schema-shaped brief and only asks for missing critical context.
- Theme and layout discovery are file-backed.
- Revision routing distinguishes deck, slide, and element scope.
- Content QA flags missing key messages, dense pages, and chart pages without data.

The runtime now connects a configurable model provider to the Design Planner,
Layout Engine, Renderer, QA gate, project state, and targeted revisions. The
remaining work is broader asset ingestion, visual QA repair, and production
provider compatibility testing.

## Agent Runner v0.2

`AgentRunner` now connects the runtime to a configurable model provider and the
existing deterministic pipeline. It writes every durable state file before
moving to the next stage, blocks rendering on content QA failures, and versions
PPTX outputs.

Luna is configured as an OpenAI-compatible endpoint:

```powershell
$env:LUNA_BASE_URL = "https://your-luna-endpoint/v1"
$env:LUNA_MODEL = "your-model-name"
$env:LUNA_API_KEY = "your-api-key"
```

Create a project when the minimum context is known:

```powershell
python -m agent.runtime start `
  --project-id market-report `
  --request "做一份新能源汽车市场分析" `
  --topic "新能源汽车市场分析" `
  --use-case work_report `
  --audience 管理层 `
  --pages 15 `
  --material-summary "已核验的年度销量数据"
```

Apply a targeted revision:

```powershell
python -m agent.runtime revise --project-id market-report --request "把第 4 页改成竞品对比"
```

`start` stops after writing `outline.json`. Review it, then continue:

```powershell
python -m agent.runtime confirm --project-id market-report
```

If critical context is missing, `start` only writes the brief and returns
`needs_clarification`; it does not spend a model call or render a speculative deck.
