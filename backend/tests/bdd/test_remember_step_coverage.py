"""The remember-flow scenarios must resolve every step they are written with."""

from pathlib import Path

from bdd.steps import remember_review
from pytest_bdd import parsers

_FEATURES = Path(__file__).resolve().parents[1] / "features" / "remember-flow"
_KEYWORDS = ("given", "when", "then")
_PREFIX = "pytestbdd_stepdef_"


def _feature_steps() -> list[tuple[str, str]]:
    steps: list[tuple[str, str]] = []
    for feature in sorted(_FEATURES.glob("*.feature")):
        keyword = ""
        for raw in feature.read_text().splitlines():
            line = raw.strip()
            head, _, rest = line.partition(" ")
            word = head.lower()
            if word in _KEYWORDS:
                keyword = word
            elif word not in ("and", "but") or not keyword:
                continue
            steps.append((keyword, rest.strip()))
    return steps


def _registered() -> list[tuple[str, str]]:
    names: list[tuple[str, str]] = []
    for name in vars(remember_review):
        if not name.startswith(_PREFIX):
            continue
        keyword, _, template = name[len(_PREFIX) :].partition("_")
        names.append((keyword, template))
    return names


def _resolves(keyword: str, text: str, registered: list[tuple[str, str]]) -> bool:
    for registered_keyword, template in registered:
        if registered_keyword != keyword:
            continue
        if template == text or parsers.parse(template).is_matching(text):
            return True
    return False


def test_every_remember_flow_step_resolves_under_its_own_keyword() -> None:
    registered = _registered()
    unresolved = sorted(
        {
            f"{keyword} {text}"
            for keyword, text in _feature_steps()
            if not _resolves(keyword, text, registered)
        }
    )

    assert unresolved == []
