"""Load all Gherkin feature files under tests/features/."""

from pathlib import Path

from pytest_bdd import scenarios

pytest_plugins = [
    "bdd.steps.capture",
    "bdd.steps.coverage_wrapup",
    "bdd.steps.draft_note",
]

_features_dir = Path(__file__).parent.parent / "features"
if any(_features_dir.rglob("*.feature")):
    scenarios(".")
