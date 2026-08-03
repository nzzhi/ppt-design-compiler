# PPT Renderer

The renderer reads `design-plan.json` as its primary input and writes an editable PowerPoint file. Content is resolved through the design plan's `content_source` reference, so semantic content and page design remain separate.

## Component dispatch

The renderer executes the Design Planner's decisions through independent page
components:

- `cover.py`: large-title / opening focal field.
- `image_story.py`: photo, illustration, and mixed evidence pages, with an
  asset path when available and a deliberate visual fallback otherwise.
- `comparison.py`: matched two-sided comparison with a decisive difference.
- `process.py`: directional process sequence.
- `timeline.py`: time-scaled milestone sequence.
- `data.py`: metric focus, chart insight, and table evidence variants.
- `conclusion.py`: synthesis and closing pages.

`renderer.py` resolves the component from `slide_type` and `visual_type`; it
does not rewrite content or infer narrative intent. The `layout-engine` package
now compiles stable frames into `render-plan.json`; migrating component geometry
to consume those frames is the next renderer step.

Image assets are read from `content_plan.slides[].assets` as strings or objects
with `path`, `file`, or `source`. Supported raster formats are PNG, JPEG, BMP,
and GIF. When no usable asset is supplied, the image component renders an
explicit visual-evidence frame and preserves the design-plan fallback.

Core slide renderers:

- `cover`
- `comparison`
- `process`
- `content` and `agenda`
- `summary`, `closing`, and `conclusion`

`timeline` currently uses the process renderer. Unsupported slide types fall back to the content renderer. Renderer modules live in `renderers/`; shared theme and typography behavior lives in `renderers/base.py`.

## Usage

```powershell
python agent/skills/ppt-renderer/renderer.py projects/<project-id>/plan/design-plan.json projects/<project-id>/outputs/presentation.pptx
```

The renderer executes decisions recorded by the Design Planner. Use
`agent.skills.layout_engine.RenderPlanCompiler` to compile a design plan against
`design-library/layouts/layout-registry.v2.json` before integrating exact frames
into a renderer component.
