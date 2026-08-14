const state = { projectId: null, jobId: null, pollTimer: null, project: null };

const $ = (selector) => document.querySelector(selector);

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  loadThemes();
  loadHealth();
  loadProjects();
});

function bindEvents() {
  $("#brief-form").addEventListener("submit", createProject);
  $("#new-project-button").addEventListener("click", showCreateView);
  $("#refresh-button").addEventListener("click", () => { loadHealth(); loadProjects(); });
  $("#confirm-button").addEventListener("click", confirmOutline);
  $("#back-to-create").addEventListener("click", showCreateView);
  $("#download-button").addEventListener("click", downloadProject);
  $("#result-download").addEventListener("click", downloadProject);
  $("#revise-button").addEventListener("click", reviseProject);
}

async function loadHealth() {
  try {
    const health = await api("/api/health");
    const pill = $("#connection-pill");
    pill.classList.toggle("connected", health.api_key_configured);
    pill.classList.toggle("error", !health.api_key_configured);
    $("#connection-text").textContent = health.api_key_configured ? "Luna 已连接" : "需要配置密钥";
    $("#model-name").textContent = `${health.provider} / ${health.model}`;
  } catch (error) {
    $("#connection-pill").classList.add("error");
    $("#connection-text").textContent = "服务未启动";
    showToast(error.message, true);
  }
}

async function loadThemes() {
  try {
    const data = await api("/api/catalog/themes");
    const select = $("#theme");
    data.themes.forEach((theme) => {
      const option = document.createElement("option");
      option.value = theme.theme_id;
      option.textContent = theme.name;
      select.appendChild(option);
    });
  } catch (error) { showToast(error.message, true); }
}

async function loadProjects() {
  try {
    const data = await api("/api/projects");
    const list = $("#project-list");
    list.replaceChildren();
    if (!data.projects.length) {
      list.innerHTML = '<div class="empty-list">还没有项目</div>';
      return;
    }
    data.projects.forEach((project) => {
      const button = document.createElement("button");
      button.className = `project-item${project.project_id === state.projectId ? " selected" : ""}`;
      button.innerHTML = `<span class="project-item-title"></span><span class="project-item-meta"></span>`;
      button.querySelector(".project-item-title").textContent = project.topic;
      button.querySelector(".project-item-meta").textContent = statusLabel(project.status);
      button.addEventListener("click", () => openProject(project.project_id));
      list.appendChild(button);
    });
    const resumable = data.projects.find((project) => ["running", "awaiting_outline_confirmation"].includes(project.status));
    if (!state.projectId && resumable) {
      await openProject(resumable.project_id);
    }
  } catch (error) { showToast(error.message, true); }
}

async function createProject(event) {
  event.preventDefault();
  const button = $("#create-button");
  button.disabled = true;
  button.innerHTML = "正在创建 <span>…</span>";
  hideToast();
  const payload = {
    topic: $("#topic").value.trim(), request: $("#request").value.trim(),
    audience: $("#audience").value.trim(), pages: Number($("#pages").value),
    use_case: $("#use-case").value, theme: $("#theme").value,
    material_summary: $("#material-summary").value.trim(),
  };
  try {
    const data = await api("/api/projects", { method: "POST", body: payload });
    state.projectId = data.project_id;
    showProjectView();
    startPolling(data.job.job_id);
    loadProjects();
  } catch (error) {
    showToast(error.message, true);
    button.disabled = false;
    button.innerHTML = "生成大纲 <span>→</span>";
  }
}

async function confirmOutline() {
  $("#confirm-button").disabled = true;
  hideToast();
  try {
    const data = await api(`/api/projects/${state.projectId}/confirm`, { method: "POST", body: {} });
    showLoading("正在生成 PPT", "Agent 正在把大纲转换成页面设计并渲染 PowerPoint");
    startPolling(data.job.job_id);
  } catch (error) {
    showToast(error.message, true);
    $("#confirm-button").disabled = false;
  }
}

async function reviseProject() {
  const request = $("#revision-request").value.trim();
  if (!request) { showToast("请先填写修改要求", true); return; }
  $("#revise-button").disabled = true;
  hideToast();
  try {
    const data = await api(`/api/projects/${state.projectId}/revise`, { method: "POST", body: { request } });
    showLoading("正在修改 PPT", "Agent 正在按你的要求生成新版本");
    startPolling(data.job.job_id);
  } catch (error) {
    showToast(error.message, true);
    $("#revise-button").disabled = false;
  }
}

function startPolling(jobId) {
  state.jobId = jobId;
  clearInterval(state.pollTimer);
  pollJob();
  state.pollTimer = setInterval(pollJob, 1200);
}

async function pollJob() {
  try {
    const job = await api(`/api/jobs/${state.jobId}`);
    updateLoading(job);
    if (["complete", "failed", "qa_failed", "awaiting_outline_confirmation", "needs_clarification"].includes(job.status)) {
      clearInterval(state.pollTimer);
      if (job.status === "failed") {
        showToast(job.error || "生成失败，请检查 Luna 配置和网络", true);
        hideLoading();
      } else if (job.status === "awaiting_outline_confirmation") {
        await openProject(state.projectId);
      } else if (job.status === "complete") {
        await openProject(state.projectId);
      } else {
        showToast(job.message, job.status === "qa_failed");
        hideLoading();
      }
      loadProjects();
    }
  } catch (error) { clearInterval(state.pollTimer); showToast(error.message, true); hideLoading(); }
}

async function openProject(projectId) {
  try {
    const project = await api(`/api/projects/${projectId}`);
    state.projectId = projectId;
    state.project = project;
    if (["awaiting_outline_confirmation", "complete", "failed", "qa_failed"].includes(project.status)) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
      state.jobId = null;
      hideLoading();
    }
    showProjectView();
    renderProject(project);
    loadProjects();
  } catch (error) { showToast(error.message, true); }
}

function renderProject(project) {
  $("#page-title").textContent = project.topic || project.project_id;
  $("#page-description").textContent = project.status === "complete" ? "检查生成结果，继续修改或下载最终文件。" : "检查 Agent 生成的大纲，确认后继续生成。";
  if (project.outline && project.status !== "complete") renderOutline(project);
  if (project.status === "complete") renderResult(project);
  updateSteps(project.status);
}

function renderOutline(project) {
  $("#loading-panel").hidden = true;
  $("#result-panel").hidden = true;
  $("#outline-panel").hidden = false;
  $("#outline-title").textContent = project.outline.deck_title;
  $("#outline-meta").textContent = `${project.outline.slides.length} 页 · ${project.outline.narrative_arc}`;
  $("#story-goal").textContent = `故事目标：${project.outline.story_goal}`;
  const list = $("#outline-list");
  list.replaceChildren();
  project.outline.slides.forEach((slide) => {
    const card = document.createElement("article");
    card.className = "outline-card";
    card.innerHTML = `<div class="outline-number">${String(slide.slide_number).padStart(2, "0")}</div><div><h3></h3><p></p></div>`;
    card.querySelector("h3").textContent = slide.working_title;
    card.querySelector("p").textContent = slide.key_message;
    list.appendChild(card);
  });
  $("#confirm-button").disabled = false;
}

function renderResult(project) {
  hideLoading();
  $("#outline-panel").hidden = true;
  $("#result-panel").hidden = false;
  $("#header-actions").hidden = false;
  $("#download-button").disabled = !project.output.available;
  $("#result-download").disabled = !project.output.available;
  const slides = project.slide_plan?.slides || [];
  $("#slide-count").textContent = `${slides.length} 页`;
  const first = slides[0];
  const preview = $("#slide-preview");
  if (!first) { preview.innerHTML = '<div class="preview-placeholder">暂无页面预览</div>'; return; }
  const bars = [35, 62, 47, 78, 54].map((height) => `<i class="preview-bar" style="height:${height}%"></i>`).join("");
  preview.innerHTML = `<div class="preview-slide"><div class="preview-kicker">01 / ${first.slide_type || "COVER"}</div><h4></h4><div class="preview-message"></div><div class="preview-bars">${bars}</div></div>`;
  preview.querySelector("h4").textContent = first.title || project.topic;
  preview.querySelector(".preview-message").textContent = first.key_message || "Agent 已完成页面设计。";
  const qa = project.qa;
  $("#qa-box").innerHTML = qa ? `<span class="qa-pass">✓ QA ${qa.status === "pass" ? "通过" : "已完成检查"}</span><br>已检查 ${qa.summary.slides_checked} 页，${qa.summary.warnings || 0} 个提示` : "等待质量检查结果";
  $("#revise-button").disabled = false;
}

function updateLoading(job) {
  if (job.status === "queued" || job.status === "running") {
    showLoading(job.operation === "revise" ? "正在修改 PPT" : "Agent 正在工作", job.message);
  }
}

function showLoading(title, message) {
  $("#loading-panel").hidden = false;
  $("#outline-panel").hidden = true;
  $("#result-panel").hidden = true;
  $("#loading-title").textContent = title;
  $("#loading-message").textContent = message;
}

function hideLoading() { $("#loading-panel").hidden = true; }
function showProjectView() { $("#create-view").hidden = true; $("#project-view").hidden = false; }
function showCreateView() { state.projectId = null; $("#create-view").hidden = false; $("#project-view").hidden = true; $("#header-actions").hidden = true; loadProjects(); }
function downloadProject() { if (state.projectId) window.location.href = `/api/projects/${state.projectId}/download`; }

function updateSteps(status) {
  const active = status === "complete" ? "deliver" : status === "awaiting_outline_confirmation" ? "outline" : "design";
  const order = ["brief", "outline", "design", "deliver"];
  document.querySelectorAll(".step").forEach((step) => {
    const current = step.dataset.step;
    step.classList.toggle("active", current === active);
    step.classList.toggle("done", order.indexOf(current) < order.indexOf(active));
  });
}

function statusLabel(status) { return { complete: "已完成", awaiting_outline_confirmation: "等待确认大纲", running: "生成中", draft: "草稿" }[status] || status || "草稿"; }
function showToast(message, error = false) { const toast = $("#toast"); toast.hidden = false; toast.classList.toggle("error", error); toast.textContent = message; }
function hideToast() { $("#toast").hidden = true; }

async function api(path, options = {}) {
  const response = await fetch(path, { method: options.method || "GET", headers: { "Content-Type": "application/json" }, body: options.body ? JSON.stringify(options.body) : undefined });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `请求失败（${response.status}）`);
  return data;
}
