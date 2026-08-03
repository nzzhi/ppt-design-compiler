"""Agent-facing orchestration primitives for the PPT design pipeline."""

from .catalog import Capability, SkillRegistry, TemplateCatalog, TemplateRecord
from .providers import ContractGenerator, LunaConfig, LunaProvider, ModelProvider, ScriptedProvider
from .runner import AgentRunner, RunResult
from .store import ProjectStore
from .workflow import IntakeResult, PresentationAgent, RevisionScope

__all__ = [
    "Capability",
    "ContractGenerator",
    "AgentRunner",
    "IntakeResult",
    "LunaConfig",
    "LunaProvider",
    "ModelProvider",
    "PresentationAgent",
    "ProjectStore",
    "RevisionScope",
    "RunResult",
    "ScriptedProvider",
    "SkillRegistry",
    "TemplateCatalog",
    "TemplateRecord",
]
