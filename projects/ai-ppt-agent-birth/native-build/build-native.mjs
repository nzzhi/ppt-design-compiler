import fs from "node:fs/promises";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT = "C:/Users/34283/Documents/New project/ppt-agent/projects/ai-ppt-agent-birth/outputs/native-ai-ppt-agent.pptx";
const W = 1280;
const H = 720;
const C = { paper: "#F7F8FA", ink: "#111827", muted: "#64748B", blue: "#2457FF", cyan: "#B8F1FF", yellow: "#F4D35E", orange: "#FF7A59", panel: "#E8ECF2", dark: "#152238" };

function box(slide, x, y, w, h, fill = "none", line = "none", geometry = "rect") {
  return slide.shapes.add({ geometry, position: { left: x, top: y, width: w, height: h }, fill, line: { style: "solid", fill: line, width: line === "none" ? 0 : 1 } });
}

function text(slide, value, x, y, w, h, size, color = C.ink, bold = false, opts = {}) {
  const shape = slide.shapes.add({ geometry: "textbox", position: { left: x, top: y, width: w, height: h }, fill: "none", line: { style: "solid", fill: "none", width: 0 } });
  shape.text = value;
  shape.text.style = { fontSize: size, color, bold, fontFamily: opts.fontFamily || "Arial", align: opts.align || "left", verticalAlign: opts.verticalAlign || "top" };
  return shape;
}

function chrome(slide, section, page) {
  text(slide, section.toUpperCase(), 56, 34, 240, 20, 13, C.blue, true);
  text(slide, String(page).padStart(2, "0"), 1180, 34, 44, 20, 13, C.muted, true, { align: "right" });
  box(slide, 56, 664, 1168, 1, C.panel);
  text(slide, "AI PPT AGENT / NATIVE PPTX", 56, 678, 300, 18, 11, C.muted, true);
}

function addSlide(presentation, fn) {
  const slide = presentation.slides.add();
  slide.background.fill = C.paper;
  fn(slide);
}

const p = Presentation.create({ slideSize: { width: W, height: H } });

addSlide(p, (s) => {
  s.background.fill = C.dark;
  box(s, 840, 0, 440, 720, C.blue);
  box(s, 930, 76, 200, 200, C.cyan, "none", "ellipse");
  box(s, 1020, 172, 180, 180, C.yellow, "none", "ellipse");
  box(s, 890, 300, 290, 290, C.orange, "none", "ellipse");
  text(s, "AI PPT AGENT", 64, 54, 300, 22, 14, C.cyan, true);
  text(s, "一个 AI PPT\nAgent 是如何诞生的", 64, 150, 730, 220, 58, "#FFFFFF", true);
  text(s, "从内容理解，到设计决策，再到可编辑的 PowerPoint。", 68, 410, 640, 60, 23, "#D4DCE8");
  text(s, "DESIGN IS A DECISION SYSTEM", 68, 606, 370, 20, 13, C.yellow, true);
});

addSlide(p, (s) => {
  chrome(s, "01 / tension", 2);
  text(s, "传统 PPT 制作的瓶颈\n不在排版，而在反复决策", 56, 100, 620, 120, 38, C.ink, true);
  text(s, "每次修改都会牵动整套页面，因为内容、叙事、视觉和输出被绑在一起。", 58, 246, 560, 60, 20, C.muted);
  const rows = [["01", "故事线", "受众、目标、重点同时变化"], ["02", "版式", "内容没有稳定的视觉映射"], ["03", "协作", "修改从局部扩散成返工"]];
  rows.forEach((r, i) => { const y = 370 + i * 78; text(s, r[0], 60, y, 48, 24, 16, C.blue, true); text(s, r[1], 140, y, 150, 26, 22, C.ink, true); text(s, r[2], 360, y, 400, 26, 18, C.muted); box(s, 140, y + 42, 680, 1, C.panel); });
  box(s, 870, 130, 280, 400, C.dark);
  text(s, "REWORK", 912, 184, 180, 22, 14, C.cyan, true);
  text(s, "∞", 900, 250, 220, 120, 96, "#FFFFFF", true, { align: "center" });
  text(s, "决策没有被记录\n所以每次都要重新猜", 916, 430, 190, 65, 18, "#D4DCE8", false, { align: "center" });
});

addSlide(p, (s) => {
  chrome(s, "02 / system", 3);
  text(s, "AI Agent 的解决方案：\n把 PPT 变成一条设计编译链", 56, 92, 650, 112, 38, C.ink, true);
  text(s, "不是直接生成页面，而是让每一个关键判断都有中间状态。", 58, 226, 620, 32, 20, C.muted);
  const nodes = [["BRIEF", "受众 / 目标", C.cyan], ["PLANNER", "叙事 / 层级", C.blue], ["RENDERER", "组件 / 几何", C.yellow], ["VALIDATOR", "视觉 / 结构", C.orange]];
  nodes.forEach((n, i) => { const x = 64 + i * 284; box(s, x, 370, 220, 150, n[2]); text(s, n[0], x + 22, 396, 180, 24, 17, C.dark, true); text(s, n[1], x + 22, 438, 180, 26, 19, C.dark); if (i < nodes.length - 1) { text(s, "→", x + 230, 416, 45, 30, 26, C.blue, true, { align: "center" }); } });
  text(s, "结构化状态 = 可解释 / 可验证 / 可局部修改", 64, 590, 600, 30, 18, C.blue, true);
});

addSlide(p, (s) => {
  chrome(s, "03 / workflow", 4);
  text(s, "Planner → Renderer → Validator", 56, 96, 820, 54, 42, C.ink, true);
  text(s, "三个角色，不再让一个模型同时猜内容、猜设计、猜几何。", 58, 172, 700, 32, 20, C.muted);
  const cols = [{ title: "Planner", color: C.blue, body: "决定\n主张 / 阅读顺序 / 密度 / 版式" }, { title: "Renderer", color: C.dark, body: "执行\n文字 / 图片 / 图表 / 连接线" }, { title: "Validator", color: C.orange, body: "检查\n溢出 / 重复 / 层级 / 叙事断点" }];
  cols.forEach((c, i) => { const x = 64 + i * 382; box(s, x, 286, 320, 248, c.color); text(s, c.title, x + 28, 318, 260, 34, 28, "#FFFFFF", true); text(s, c.body, x + 28, 382, 260, 100, 22, "#FFFFFF"); text(s, `0${i + 1}`, x + 260, 486, 40, 22, 14, c.color === C.orange ? C.yellow : C.cyan, true, { align: "right" }); });
  text(s, "每一次修改，都应该落回某一个决策层。", 64, 596, 650, 28, 18, C.blue, true);
});

addSlide(p, (s) => {
  chrome(s, "04 / contrast", 5);
  text(s, "传统工具 vs AI PPT Agent", 56, 94, 760, 52, 42, C.ink, true);
  text(s, "差异不在于有没有画布，而在于设计判断是否可复用。", 58, 166, 720, 30, 20, C.muted);
  box(s, 64, 284, 500, 282, C.panel);
  box(s, 716, 284, 500, 282, C.blue);
  text(s, "TRADITIONAL TOOL", 96, 322, 260, 20, 13, C.muted, true);
  text(s, "AI PPT AGENT", 748, 322, 260, 20, 13, C.cyan, true);
  ["画布和模板", "手工判断", "整页返工"].forEach((v, i) => text(s, v, 96, 386 + i * 48, 300, 30, 25, C.ink, true));
  ["语义计划", "可解释决策", "局部修改"].forEach((v, i) => text(s, v, 748, 386 + i * 48, 300, 30, 25, "#FFFFFF", true));
  text(s, "从“帮你画页面”\n到“帮你持续做正确决策”", 64, 602, 720, 36, 22, C.blue, true);
});

addSlide(p, (s) => {
  s.background.fill = C.blue;
  text(s, "ENDING", 64, 54, 200, 22, 14, C.cyan, true);
  text(s, "AI 不会替代设计师。\n它会让设计决策变得可规模化。", 64, 150, 920, 190, 54, "#FFFFFF", true);
  text(s, "一个优秀的 AI PPT Agent，交付的不只是文件，而是一套能持续改进的演示设计能力。", 68, 430, 760, 72, 24, "#E8F1FF");
  box(s, 64, 600, 360, 5, C.yellow);
  text(s, "CONTENT → DESIGN → EDITABLE OUTPUT", 64, 632, 550, 20, 14, C.cyan, true);
});

const pptx = await PresentationFile.exportPptx(p);
await pptx.save(OUT);
console.log(`Generated ${OUT}`);
