from __future__ import annotations

import json
import mimetypes
import os
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from agent.runtime import AgentRunner, LunaProvider, ProjectStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = PROJECT_ROOT / "projects"
STATIC_ROOT = PROJECT_ROOT / "app" / "static"
PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")


class WorkbenchState:
    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ppt-agent")
        self.lock = threading.Lock()
        self.jobs: dict[str, dict[str, Any]] = {}

    def submit(self, project_id: str, operation: str, action: Callable[[], Any]) -> dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        now = _now()
        with self.lock:
            self.jobs[job_id] = {
                "job_id": job_id,
                "project_id": project_id,
                "operation": operation,
                "status": "queued",
                "message": "等待 Agent 处理",
                "created_at": now,
                "updated_at": now,
                "result": None,
                "error": None,
            }
        self.executor.submit(self._run, job_id, action)
        return self.get(job_id) or {}

    def _run(self, job_id: str, action: Callable[[], Any]) -> None:
        self._update(job_id, status="running", message="Agent 正在生成，请稍候")
        try:
            result = action()
            self._update(
                job_id,
                status="complete" if result.status == "complete" else result.status,
                message=_status_message(result.status),
                result=_result_dict(result),
            )
        except Exception as error:  # surfaced in the UI as a user-readable job error
            self._update(job_id, status="failed", message="生成失败", error=str(error))

    def _update(self, job_id: str, **changes: Any) -> None:
        with self.lock:
            if job_id not in self.jobs:
                return
            self.jobs[job_id].update(changes, updated_at=_now())

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self.lock:
            job = self.jobs.get(job_id)
            return dict(job) if job else None


WORKBENCH = WorkbenchState()


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), WorkbenchHandler)


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = create_server(host, port)
    print(f"PPT Agent Workbench: http://{host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nWorkbench stopped.")
    finally:
        server.server_close()
        WORKBENCH.executor.shutdown(wait=False, cancel_futures=True)


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "PPTAgentWorkbench/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path == "/" or path == "/index.html":
                return self._static("index.html")
            if path.startswith("/assets/"):
                return self._static(path.removeprefix("/assets/"))
            if path == "/api/health":
                return self._json(HTTPStatus.OK, _health())
            if path == "/api/catalog/themes":
                return self._json(HTTPStatus.OK, {"themes": _themes()})
            if path == "/api/projects":
                return self._json(HTTPStatus.OK, {"projects": _list_projects()})
            if path.startswith("/api/jobs/"):
                job = WORKBENCH.get(path.removeprefix("/api/jobs/"))
                if not job:
                    return self._error(HTTPStatus.NOT_FOUND, "找不到这个任务")
                return self._json(HTTPStatus.OK, job)
            project_id, suffix = _project_route(path)
            if project_id and suffix == "":
                return self._json(HTTPStatus.OK, _project_snapshot(project_id))
            if project_id and suffix == "/download":
                return self._download(project_id)
            return self._error(HTTPStatus.NOT_FOUND, "找不到这个页面")
        except (ValueError, FileNotFoundError) as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))
        except Exception as error:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            payload = self._body()
            if path == "/api/projects":
                return self._create_project(payload)
            project_id, suffix = _project_route(path)
            if project_id and suffix == "/confirm":
                return self._queue_project_action(project_id, "confirm", lambda: AgentRunner(PROJECT_ROOT, LunaProvider.from_env(), projects_root=PROJECTS_ROOT).confirm_outline(project_id))
            if project_id and suffix == "/revise":
                request = str(payload.get("request", "")).strip()
                if not request:
                    return self._error(HTTPStatus.BAD_REQUEST, "请填写修改要求")
                return self._queue_project_action(project_id, "revise", lambda: AgentRunner(PROJECT_ROOT, LunaProvider.from_env(), projects_root=PROJECTS_ROOT).revise(project_id, request))
            return self._error(HTTPStatus.NOT_FOUND, "找不到这个接口")
        except (ValueError, FileNotFoundError) as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))
        except Exception as error:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))

    def _create_project(self, payload: dict[str, Any]) -> None:
        topic = str(payload.get("topic", "")).strip()
        request = str(payload.get("request", topic)).strip()
        if not topic or not request:
            return self._error(HTTPStatus.BAD_REQUEST, "请填写 PPT 主题和需求描述")
        project_id = _new_project_id(payload.get("project_id"), topic)
        audience = _as_strings(payload.get("audience")) or ["管理层"]
        page_count = _bounded_int(payload.get("pages", 10), 3, 40)
        use_case = str(payload.get("use_case", "work_report"))
        theme = str(payload.get("theme", "auto"))
        material = str(payload.get("material_summary", "")).strip() or "按用户需求整理，等待模型补充表达结构"
        materials = [{"material_id": "material-001", "type": "text", "summary": material}]
        job = WORKBENCH.submit(
            project_id,
            "start",
            lambda: AgentRunner(PROJECT_ROOT, LunaProvider.from_env(), projects_root=PROJECTS_ROOT).start(
                    project_id=project_id,
                    raw_request=request,
                    topic=topic,
                    use_case=use_case,
                    audience=audience,
                    page_count=page_count,
                    theme_hint=theme,
                    requested_style=payload.get("style"),
                    materials=materials,
                ),
        )
        return self._json(HTTPStatus.ACCEPTED, {"project_id": project_id, "job": job})

    def _queue_project_action(self, project_id: str, operation: str, action: Callable[[], Any]) -> None:
        if not (PROJECTS_ROOT / project_id).is_dir():
            return self._error(HTTPStatus.NOT_FOUND, "找不到这个项目")
        return self._json(HTTPStatus.ACCEPTED, {"project_id": project_id, "job": WORKBENCH.submit(project_id, operation, action)})

    def _static(self, relative_path: str) -> None:
        path = (STATIC_ROOT / relative_path).resolve()
        if STATIC_ROOT not in path.parents or not path.is_file():
            return self._error(HTTPStatus.NOT_FOUND, "找不到静态文件")
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def _download(self, project_id: str) -> None:
        store = ProjectStore(PROJECTS_ROOT, project_id)
        files = sorted((store.root / "outputs").glob("presentation-v*.pptx"))
        if not files:
            return self._error(HTTPStatus.NOT_FOUND, "这个项目还没有生成 PPT")
        path = files[-1]
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        self.send_header("Content-Disposition", f'attachment; filename="{project_id}.pptx"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("请求内容过大")
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("请求必须是 JSON 对象")
        return payload

    def _json(self, status: HTTPStatus, value: Any) -> None:
        body = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: HTTPStatus, message: str) -> None:
        return self._json(status, {"error": message})

    def log_message(self, format: str, *args: Any) -> None:
        return


def _project_route(path: str) -> tuple[str | None, str]:
    prefix = "/api/projects/"
    if not path.startswith(prefix):
        return None, ""
    remainder = path[len(prefix):].strip("/")
    bits = remainder.split("/", 1)
    project_id = bits[0]
    if not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise ValueError("非法项目编号")
    return project_id, (f"/{bits[1]}" if len(bits) == 2 else "")


def _new_project_id(requested: Any, topic: str) -> str:
    if requested:
        candidate = re.sub(r"[^a-z0-9-]+", "-", str(requested).lower()).strip("-")
        if PROJECT_ID_PATTERN.fullmatch(candidate):
            return candidate
    return f"ppt-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"


def _health() -> dict[str, Any]:
    provider = LunaProvider.from_env()
    return {
        "status": "ok",
        "provider": "Luna",
        "base_url": provider.config.base_url,
        "model": provider.config.model,
        "api_key_configured": bool(provider.config.api_key),
    }


def _themes() -> list[dict[str, Any]]:
    from agent.runtime import TemplateCatalog

    return [
        {
            "theme_id": item.theme_id,
            "name": item.name,
            "use_cases": list(item.use_cases),
            "audience": list(item.audience),
            "default_slide_types": list(item.default_slide_types),
        }
        for item in TemplateCatalog(PROJECT_ROOT).themes()
    ]


def _list_projects() -> list[dict[str, Any]]:
    projects = []
    for path in sorted(PROJECTS_ROOT.iterdir()) if PROJECTS_ROOT.is_dir() else []:
        if not path.is_dir() or not PROJECT_ID_PATTERN.fullmatch(path.name):
            continue
        try:
            projects.append(_project_snapshot(path.name))
        except Exception:
            continue
    return sorted(projects, key=lambda item: item.get("updated_at", ""), reverse=True)


def _project_snapshot(project_id: str) -> dict[str, Any]:
    store = ProjectStore(PROJECTS_ROOT, project_id)
    brief = _read_optional(store, "plan/brief.json")
    outline = _read_optional(store, "plan/outline.json")
    slide_plan = _read_optional(store, "plan/slide-plan.json")
    qa = _read_optional(store, "qa/qa-report.json")
    session = _read_optional(store, "input/session.json") or {}
    outputs = sorted((store.root / "outputs").glob("presentation-v*.pptx"))
    return {
        "project_id": project_id,
        "status": session.get("status", "draft"),
        "next_action": session.get("next_action"),
        "topic": (brief or {}).get("topic", project_id),
        "brief": brief,
        "outline": outline,
        "slide_plan": slide_plan,
        "qa": qa,
        "output": {"available": bool(outputs), "filename": outputs[-1].name if outputs else None},
        "updated_at": datetime.fromtimestamp(store.root.stat().st_mtime, UTC).isoformat(),
    }


def _read_optional(store: ProjectStore, path: str) -> dict[str, Any] | None:
    return store.read_json(path) if store.exists(path) else None


def _result_dict(result: Any) -> dict[str, Any]:
    return {
        "project_id": result.project_id,
        "status": result.status,
        "next_action": result.next_action,
        "project_path": str(result.project_path),
        "output_path": str(result.output_path) if result.output_path else None,
        "qa_report_path": str(result.qa_report_path) if result.qa_report_path else None,
    }


def _status_message(status: str) -> str:
    return {
        "awaiting_outline_confirmation": "大纲已生成，请检查后确认",
        "complete": "PPT 已生成，可以下载或继续修改",
        "qa_failed": "质量检查未通过，请根据提示修改",
        "needs_clarification": "还需要补充一些信息",
    }.get(status, f"当前状态：{status}")


def _as_strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _bounded_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return minimum


def _now() -> str:
    return datetime.now(UTC).isoformat()
