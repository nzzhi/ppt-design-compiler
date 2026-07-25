# Component Catalog

MVP components are simple PowerPoint-native objects. They must remain editable after rendering.

| Component | PowerPoint representation | Common use |
| --- | --- | --- |
| Title text | Text box | Slide title |
| Key message | Text box or callout shape | One-sentence conclusion |
| Bullet group | Text box | Supporting points |
| Metric block | Text box plus simple shape | Big-number slide |
| Two-column compare | Grouped shapes and text boxes | Comparison slide |
| Timeline | Lines, shapes, and text boxes | Time sequence |
| Process steps | Shapes and connectors | Workflow |
| Chart placeholder | Native chart where possible | Data visual |
| Image frame | Image plus optional caption | User-provided images |
| Footer note | Text box | Sources, caveats, metadata |

Every component instance should be represented in `editable_elements` with a stable `element_id`.

