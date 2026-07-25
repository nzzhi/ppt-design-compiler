# PPT Design Skill

一个本地优先的 AI 演示文稿设计 Skill / PPT design compiler。

它把“用户想讲什么”逐步转换为“每一页应该如何表达”，并生成可编辑的 PowerPoint：

```text
用户需求 -> brief -> outline -> slide-plan -> design-plan -> renderer -> PPTX
```

## 它解决什么问题

普通 PPT 生成器往往只是把文字放进文本框。本项目把内容规划和视觉设计拆成独立阶段，使每页能够明确描述页面类型、布局、视觉形式、信息密度、设计说明、素材需求和质量约束。

渲染器根据 `design-plan.json` 选择不同页面渲染器，而不是所有页面使用同一种文本布局。

## 成品示例

以下是当前 renderer 生成的实际页面预览：

![Design-plan output](docs/showcase/design-plan-output.png)

![Agent concept output](docs/showcase/agent-concept-output.png)

这些图片用于展示当前能力边界，不代表最终模板库的视觉上限。

## 当前状态

已实现：

- v2 结构化 schema（brief、outline、slide-plan、design-plan、render-plan）
- Design Planner：从内容计划生成页面设计决策
- 页面类型规则、布局选择规则和基础设计规范知识库
- 模块化 PPTX renderer
- cover、content、comparison、process、conclusion 等核心页面类型
- 可编辑的 `python-pptx` 输出

进行中：

- 真正的 Layout Engine 和 render-plan 解析
- 图片、图表和视觉素材的自动解析
- 视觉 QA、溢出检测和自动修复循环
- 面向完整 Agent 的需求澄清、素材读取和任务编排

## 项目结构

```text
agent/                  核心契约、schema 和可调用 Skills
design-library/         页面、布局和设计知识库
docs/                   架构与产品文档
tests/                  自动化测试
```

## 使用方式

先阅读 `docs/architecture/v2-design-compiler.md`、`docs/architecture/design-planner.md`、`agent/skills/design-planner/README.md` 和 `agent/skills/ppt-renderer/README.md`。

本项目当前是可被上层 Agent 调用的设计与渲染能力包，并不宣称已经完成完整自主 Agent loop。

## 参考与独立实现声明

本项目独立实现，研究和借鉴了开源 AI 演示文稿工具与设计 Skill 的公开思想，包括页面类型、设计系统、布局规划和质量检查等方向。未复制第三方源代码、模板或素材。特别感谢 [Mck-ppt-design-skill](https://github.com/likaku/Mck-ppt-design-skill) 等项目提供的研究参考。

## 路线图

目标是从可复用的 PPT Design Skill 演进为完整的本地 AI PPT Agent：

```text
需求理解 -> 故事线规划 -> 设计规划 -> 布局求解 -> 渲染 -> 视觉检查 -> 修复 -> 交付
```

## License

许可证将在首次公开发布前确定。第三方依赖仍以其各自许可证为准。
