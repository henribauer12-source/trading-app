"""Check level 0: the environment itself.

These tests check no domain logic, but whether the dependency decisions from
DEPENDENCIES.md are actually in the environment. If something turns red here,
an approval has been circumvented — not a feature broken.
"""

import importlib
import importlib.util
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Module name -> expected version, exactly as approved in DEPENDENCIES.md.
APPROVED = {
    "duckdb": "1.5.5",
    "pandas": "3.0.6",
    "numpy": "2.5.3",
    "pyarrow": "25.0.1",
    "pydantic": "2.13.5",
    "exchange_calendars": "4.13.2",
    "yfinance": "1.7.0",
    "pytest": "9.1.1",
    "hypothesis": "6.168.1",
}


@pytest.mark.parametrize(("module", "version"), sorted(APPROVED.items()))
def test_approved_version_is_installed(module: str, version: str) -> None:
    """No package may deviate unnoticed from the approved version."""
    mod = importlib.import_module(module)
    assert mod.__version__ == version, (
        f"{module}: installed {mod.__version__}, approved {version}. "
        f"A deviation needs a new entry in DEPENDENCIES.md."
    )


def test_apscheduler_stays_below_version_4() -> None:
    """APScheduler 4.x is alpha and blocked according to the audit protocol."""
    import apscheduler

    major = int(apscheduler.__version__.split(".")[0])
    assert major == 3, (
        f"APScheduler {apscheduler.__version__} installed. "
        f"4.x is alpha and blocked — see DEPENDENCIES.md."
    )


def test_blocked_packages_are_not_installed() -> None:
    """Explicitly rejected packages must not come in by a detour."""
    blocked = ["polars", "pandas_market_calendars"]
    found = []
    for name in blocked:
        if importlib.util.find_spec(name) is not None:
            found.append(name)
    assert not found, (
        f"Blocked packages installed: {found}. "
        f"Either slipped in as a transitive dependency or installed by hand."
    )


def test_lockfile_matches_pyproject() -> None:
    """The lockfile must match the declared direct dependencies."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((PROJECT_ROOT / "uv.lock").read_text())

    declared = set()
    for line in pyproject["project"]["dependencies"]:
        name = line.split("=")[0].split(">")[0].split("<")[0].strip()
        declared.add(name.lower().replace("_", "-"))

    locked = {p["name"].lower() for p in lock["package"]}
    missing = declared - locked
    assert not missing, f"Declared in pyproject but not in the lockfile: {missing}"


def _exact_pins(pyproject: dict) -> dict[str, str]:
    """All dependencies pinned with == in pyproject, name -> version."""
    lines = list(pyproject["project"]["dependencies"])
    lines += pyproject.get("dependency-groups", {}).get("dev", [])
    pins = {}
    for line in lines:
        if "==" not in line:
            continue
        name, version = line.split("==", 1)
        pins[name.strip().lower().replace("_", "-")] = version.strip()
    return pins


def test_pyproject_pins_match_lockfile() -> None:
    """A pin in pyproject must correspond exactly to the version in the lockfile.

    Without this test a pin line edited by hand stays unnoticed as long as the
    old environment is still installed.
    """
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((PROJECT_ROOT / "uv.lock").read_text())
    locked = {p["name"].lower(): p.get("version") for p in lock["package"]}

    deviations = []
    for name, version in _exact_pins(pyproject).items():
        if locked.get(name) != version:
            deviations.append(f"{name}: pyproject=={version}, lock=={locked.get(name)}")
    assert not deviations, (
        "pyproject and uv.lock drift apart: "
        + "; ".join(deviations)
        + ". Run `uv lock` and send the new version through the audit protocol."
    )


def test_pyproject_pins_match_installation() -> None:
    """A pin in pyproject must correspond to the version that is actually importable."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    # Distribution name -> import name, where they differ.
    import_name = {"exchange-calendars": "exchange_calendars"}

    deviations = []
    for name, version in _exact_pins(pyproject).items():
        module = import_name.get(name, name.replace("-", "_"))
        try:
            mod = importlib.import_module(module)
        except ImportError:
            deviations.append(f"{name}: pinned to {version}, but not importable")
            continue
        installed = getattr(mod, "__version__", None)
        if installed != version:
            deviations.append(f"{name}: pyproject=={version}, installed=={installed}")
    assert not deviations, (
        "pyproject and environment drift apart: "
        + "; ".join(deviations)
        + ". Run `uv sync`."
    )


def test_no_unaudited_direct_dependencies() -> None:
    """Every direct dependency needs a line in DEPENDENCIES.md."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    protocol = (PROJECT_ROOT / "DEPENDENCIES.md").read_text().lower()

    all_deps = list(pyproject["project"]["dependencies"])
    all_deps += pyproject.get("dependency-groups", {}).get("dev", [])

    unaudited = []
    for line in all_deps:
        name = line.split("=")[0].split(">")[0].split("<")[0].strip().lower()
        if name not in protocol:
            unaudited.append(name)
    assert not unaudited, (
        f"Without an entry in DEPENDENCIES.md: {unaudited}. "
        f"Go through the audit protocol before this is checked in."
    )
