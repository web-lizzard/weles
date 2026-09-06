"""Load all Gherkin feature files under tests/features/."""

from pathlib import Path

from pytest_bdd import scenarios

pytest_plugins = [
    "bdd.steps.approve_outbox",
    "bdd.steps.capture",
    "bdd.steps.coverage_wrapup",
    "bdd.steps.distill",
    "bdd.steps.draft_note",
    "bdd.steps.note_list",
    "bdd.steps.vocabulary_reuse",
]

_features_dir = Path(__file__).parent.parent / "features"
if any(_features_dir.rglob("*.feature")):
    scenarios(".")
