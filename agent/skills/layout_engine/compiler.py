from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_SOURCE = Path(__file__).resolve().parent.parent / "layout-engine" / "compiler.py"
_SPEC = spec_from_file_location("ppt_agent_layout_engine_source", _SOURCE)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load layout engine source: {_SOURCE}")
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
RenderPlanCompiler = _MODULE.RenderPlanCompiler

__all__ = ["RenderPlanCompiler"]
