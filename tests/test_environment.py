"""Prüfebene 0: das Environment selbst.

Diese Tests prüfen keine Fachlogik, sondern ob die Abhängigkeitsentscheidungen
aus DEPENDENCIES.md tatsächlich im Environment stehen. Wenn hier etwas rot wird,
ist eine Freigabe unterlaufen worden — nicht ein Feature kaputt.
"""

import importlib
import importlib.util
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Modulname -> erwartete Version, exakt wie in DEPENDENCIES.md freigegeben.
FREIGEGEBEN = {
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


@pytest.mark.parametrize(("modul", "version"), sorted(FREIGEGEBEN.items()))
def test_freigegebene_version_ist_installiert(modul: str, version: str) -> None:
    """Kein Paket darf unbemerkt von der freigegebenen Version abweichen."""
    mod = importlib.import_module(modul)
    assert mod.__version__ == version, (
        f"{modul}: installiert {mod.__version__}, freigegeben {version}. "
        f"Abweichung braucht einen neuen Eintrag in DEPENDENCIES.md."
    )


def test_apscheduler_bleibt_unter_version_4() -> None:
    """APScheduler 4.x ist Alpha und laut Prüfprotokoll gesperrt."""
    import apscheduler

    major = int(apscheduler.__version__.split(".")[0])
    assert major == 3, (
        f"APScheduler {apscheduler.__version__} installiert. "
        f"4.x ist Alpha und gesperrt — siehe DEPENDENCIES.md."
    )


def test_gesperrte_pakete_sind_nicht_installiert() -> None:
    """Explizit abgelehnte Pakete dürfen nicht über Umwege hereinkommen."""
    gesperrt = ["polars", "pandas_market_calendars"]
    gefunden = []
    for name in gesperrt:
        if importlib.util.find_spec(name) is not None:
            gefunden.append(name)
    assert not gefunden, (
        f"Gesperrte Pakete installiert: {gefunden}. "
        f"Entweder als transitive Abhängigkeit hereingerutscht oder von Hand installiert."
    )


def test_lockfile_deckt_sich_mit_pyproject() -> None:
    """Das Lockfile muss zu den deklarierten direkten Abhängigkeiten passen."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((PROJECT_ROOT / "uv.lock").read_text())

    deklariert = set()
    for zeile in pyproject["project"]["dependencies"]:
        name = zeile.split("=")[0].split(">")[0].split("<")[0].strip()
        deklariert.add(name.lower().replace("_", "-"))

    gelockt = {p["name"].lower() for p in lock["package"]}
    fehlend = deklariert - gelockt
    assert not fehlend, f"In pyproject deklariert, aber nicht im Lockfile: {fehlend}"


def _exakte_pins(pyproject: dict) -> dict[str, str]:
    """Alle mit == gepinnten Abhängigkeiten aus pyproject, Name -> Version."""
    zeilen = list(pyproject["project"]["dependencies"])
    zeilen += pyproject.get("dependency-groups", {}).get("dev", [])
    pins = {}
    for zeile in zeilen:
        if "==" not in zeile:
            continue
        name, version = zeile.split("==", 1)
        pins[name.strip().lower().replace("_", "-")] = version.strip()
    return pins


def test_pyproject_pins_decken_sich_mit_lockfile() -> None:
    """Ein Pin in pyproject muss exakt der Version im Lockfile entsprechen.

    Ohne diesen Test bleibt eine von Hand geänderte Pin-Zeile unbemerkt,
    solange das alte Environment noch installiert ist.
    """
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((PROJECT_ROOT / "uv.lock").read_text())
    gelockt = {p["name"].lower(): p.get("version") for p in lock["package"]}

    abweichungen = []
    for name, version in _exakte_pins(pyproject).items():
        if gelockt.get(name) != version:
            abweichungen.append(f"{name}: pyproject=={version}, lock=={gelockt.get(name)}")
    assert not abweichungen, (
        "pyproject und uv.lock driften auseinander: "
        + "; ".join(abweichungen)
        + ". `uv lock` laufen lassen und die neue Version durch das Prüfprotokoll schicken."
    )


def test_pyproject_pins_decken_sich_mit_installation() -> None:
    """Ein Pin in pyproject muss der tatsächlich importierbaren Version entsprechen."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    # Verteilungsname -> Importname, wo sie sich unterscheiden.
    importname = {"exchange-calendars": "exchange_calendars"}

    abweichungen = []
    for name, version in _exakte_pins(pyproject).items():
        modul = importname.get(name, name.replace("-", "_"))
        try:
            mod = importlib.import_module(modul)
        except ImportError:
            abweichungen.append(f"{name}: gepinnt auf {version}, aber nicht importierbar")
            continue
        installiert = getattr(mod, "__version__", None)
        if installiert != version:
            abweichungen.append(f"{name}: pyproject=={version}, installiert=={installiert}")
    assert not abweichungen, (
        "pyproject und Environment driften auseinander: "
        + "; ".join(abweichungen)
        + ". `uv sync` laufen lassen."
    )


def test_keine_ungeprueften_direkten_abhaengigkeiten() -> None:
    """Jede direkte Abhängigkeit braucht eine Zeile in DEPENDENCIES.md."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    protokoll = (PROJECT_ROOT / "DEPENDENCIES.md").read_text().lower()

    alle = list(pyproject["project"]["dependencies"])
    alle += pyproject.get("dependency-groups", {}).get("dev", [])

    ungeprueft = []
    for zeile in alle:
        name = zeile.split("=")[0].split(">")[0].split("<")[0].strip().lower()
        if name not in protokoll:
            ungeprueft.append(name)
    assert not ungeprueft, (
        f"Ohne Eintrag in DEPENDENCIES.md: {ungeprueft}. "
        f"Prüfprotokoll durchlaufen, bevor das eingecheckt wird."
    )
