"""Replay every scenario of evals/scenarios/ against the REAL LLM and print the pass rate.

Usage: uv run python evals/run_evals.py [--only <id or category>]
Costs a little money: each scenario makes a few calls to the Anthropic API.
"""

import argparse
import sys
from pathlib import Path

from voxmail.config import get_settings
from voxmail.contacts.directory import JsonContactDirectory
from voxmail.evaluation import load_scenarios, run_scenario
from voxmail.llm.anthropic_client import AnthropicLLM

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
TARGET = 0.90


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="run only scenarios with this id or category")
    args = parser.parse_args()

    settings = get_settings()
    if settings.anthropic_api_key is None:
        print("❌ ANTHROPIC_API_KEY manquante. Ajoutez-la dans le fichier .env.")
        return 1
    llm = AnthropicLLM(settings.anthropic_api_key.get_secret_value(), settings.anthropic_model)
    contacts = JsonContactDirectory(settings.contacts_file)

    scenarios = load_scenarios(SCENARIOS_DIR)
    if args.only:
        scenarios = [s for s in scenarios if args.only in (s.id, s.category)]

    passed = 0
    for scenario in scenarios:
        result = run_scenario(scenario, llm, contacts, settings.scoring())
        passed += result.passed
        print(f"{'✅' if result.passed else '❌'} [{scenario.category}] {scenario.id}")
        for failure in result.failures:
            print(f"     {failure}")

    rate = passed / len(scenarios) if scenarios else 0.0
    print(f"\n{passed}/{len(scenarios)} scénarios réussis ({rate:.0%}), objectif {TARGET:.0%}")
    return 0 if rate >= TARGET else 1


if __name__ == "__main__":
    sys.exit(main())
