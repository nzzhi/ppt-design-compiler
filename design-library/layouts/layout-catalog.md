# Layout Catalog

The MVP renderer should support a small, stable layout set before adding decorative variation.

| Layout ID | Slide type | Purpose |
| --- | --- | --- |
| `cover.title-subtitle.v1` | `cover` | Title, subtitle, context metadata |
| `agenda.numbered-list.v1` | `agenda` | 3 to 6 agenda items |
| `content.title-body.v1` | `content` | One key message plus supporting bullets |
| `summary.three-takeaways.v1` | `summary` | Three major conclusions |
| `comparison.two-column.v1` | `comparison` | Compare two options, markets, products, or stages |
| `big-number.metric-focus.v1` | `big-number` | One metric, short explanation, optional footnote |
| `timeline.horizontal.v1` | `timeline` | 3 to 6 time steps |
| `process.steps.v1` | `process` | Sequential workflow or method |
| `chart.title-insight.v1` | `chart` | Chart with explicit conclusion |
| `closing.final-message.v1` | `closing` | Final conclusion and optional call to action |

Each layout must reserve fixed regions for title, key message, body, visual, and footnotes so QA can detect overflow and overlap.

