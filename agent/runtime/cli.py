from __future__ import annotations

import argparse
import json
from pathlib import Path

from .providers import LunaProvider
from .runner import AgentRunner


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PPT Agent workflow.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    intake = subparsers.add_parser("start", help="Create a project and run when context is complete.")
    intake.add_argument("--project-id", required=True)
    intake.add_argument("--request", required=True)
    intake.add_argument("--topic", required=True)
    intake.add_argument("--use-case", required=True, choices=["classroom", "defense", "work_report", "roadshow", "client_briefing", "other"])
    intake.add_argument("--audience", action="append", default=[])
    intake.add_argument("--pages", type=int, default=10)
    intake.add_argument("--theme", default="auto")
    intake.add_argument("--material-summary", action="append", default=[])

    run_brief = subparsers.add_parser("run-brief", help="Run a confirmed brief JSON.")
    run_brief.add_argument("brief")

    confirm = subparsers.add_parser("confirm", help="Confirm the saved outline and generate the deck.")
    confirm.add_argument("--project-id", required=True)

    revise = subparsers.add_parser("revise", help="Apply one targeted revision.")
    revise.add_argument("--project-id", required=True)
    revise.add_argument("--request", required=True)

    args = parser.parse_args()
    runner = AgentRunner(PROJECT_ROOT, LunaProvider.from_env())
    if args.command == "start":
        materials = [
            {"material_id": f"material-{index:03d}", "type": "other", "summary": summary}
            for index, summary in enumerate(args.material_summary, 1)
        ]
        result = runner.start(
            project_id=args.project_id,
            raw_request=args.request,
            topic=args.topic,
            use_case=args.use_case,
            audience=args.audience,
            page_count=args.pages,
            theme_hint=args.theme,
            materials=materials,
        )
    elif args.command == "run-brief":
        brief = json.loads(Path(args.brief).read_text(encoding="utf-8"))
        result = runner.run_brief(brief)
    elif args.command == "confirm":
        result = runner.confirm_outline(args.project_id)
    else:
        result = runner.revise(args.project_id, args.request)
    print(json.dumps(_result_dict(result), ensure_ascii=False, indent=2))


def _result_dict(result) -> dict[str, object]:
    return {
        "project_id": result.project_id,
        "status": result.status,
        "next_action": result.next_action,
        "project_path": str(result.project_path),
        "output_path": str(result.output_path) if result.output_path else None,
        "qa_report_path": str(result.qa_report_path) if result.qa_report_path else None,
    }


if __name__ == "__main__":
    main()
