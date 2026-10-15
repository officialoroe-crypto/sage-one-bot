from __future__ import annotations

import argparse
from pathlib import Path

from dev_agent.agent import DevelopmentAgent


def main() -> int:
    parser = argparse.ArgumentParser(description="SAGE ONE controlled development agent")
    parser.add_argument("task", nargs="+", help="Development task for SAGE")
    parser.add_argument("--workspace", default=".", help="SAGE repository root")
    parser.add_argument("--apply", action="store_true", help="Allow source/test file writes")
    parser.add_argument("--max-iterations", type=int, default=12)
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    agent = DevelopmentAgent(str(workspace), apply_changes=args.apply)
    result = agent.run(" ".join(args.task), max_iterations=args.max_iterations)
    print(agent.to_json(result))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
