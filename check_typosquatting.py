#!/usr/bin/env python3
"""
Typosquatting-Detektor für requirements-Dateien.
Prüft jeden Paketnamen gegen eine Liste populärer PyPI-Pakete:
- verdächtig ähnlicher Name (difflib-ratio über Schwelle, aber nicht identisch)
- UND existiert selbst nicht auf PyPI (404) -> starkes Typo-Signal
Exit-Code 1 bei Fund (failt die GitHub Action), sonst 0.
"""

import sys
import difflib
import json
import urllib.request
import urllib.error

POPULAR = [
    "requests", "numpy", "pandas", "flask", "django", "setuptools",
    "pip", "wheel", "scipy", "pytest", "urllib3", "certifi", "click",
    "jinja2", "pyyaml", "cryptography", "boto3", "fastapi", "pydantic",
]
THRESHOLD = 0.85
REQUIREMENTS_FILE = sys.argv[1] if len(sys.argv) > 1 else "requirements-ci.txt"

SEPARATORS = ["==", ">=", "<=", "~=", "!=", ">", "<", "["]


def parse_requirements(path):
    """Extrahiert reine Paketnamen; ignoriert Kommentare, Leerzeilen,
    lokale Pfade (./ oder /), Optionen (--hash etc.) und Version-Pins."""
    names = []
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("-") or line.startswith("."):
                    continue  # Optionen (--hash) und lokale Pfade
                if "/" in line:
                    continue  # lokale Pfade / URLs
                token = line.split()[0]  # alles nach erstem Leerzeichen weg
                for sep in SEPARATORS:
                    if sep in token:
                        token = token.split(sep)[0]
                name = token.strip().lower()
                if name:
                    names.append(name)
    except FileNotFoundError:
        print(f"[ERROR] File not found: {path}")
        sys.exit(2)
    return names


def closest_popular(name):
    """Gibt (referenz, ratio) des ähnlichsten populären Pakets zurück."""
    best_ref, best_ratio = None, 0.0
    for ref in POPULAR:
        ratio = difflib.SequenceMatcher(None, name, ref).ratio()
        if ratio > best_ratio:
            best_ref, best_ratio = ref, ratio
    return best_ref, best_ratio


def exists_on_pypi(name):
    """True wenn Paket auf PyPI existiert (HTTP 200), False bei 404."""
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        print(f"[WARN] PyPI returned {e.code} for '{name}', treating as existing.")
        return True  # im Zweifel nicht fälschlich Alarm schlagen
    except urllib.error.URLError as e:
        print(f"[WARN] PyPI unreachable for '{name}' ({e.reason}); skipping API check.")
        return True  # Netzproblem -> nicht blockieren, nur Distanz zählt


def main():
    print(f"Scanning '{REQUIREMENTS_FILE}' for typosquatting...\n")
    names = parse_requirements(REQUIREMENTS_FILE)
    if not names:
        print("No PyPI package names to check.")
        sys.exit(0)

    suspicious = []
    for name in names:
        ref, ratio = closest_popular(name)

        if name in POPULAR:
            print(f"  OK        {name:20} (known popular package)")
            continue

        if ratio >= THRESHOLD:
            # ähnlich zu einem populären Paket -> PyPI gegenchecken
            on_pypi = exists_on_pypi(name)
            if not on_pypi:
                print(f"  SUSPECT   {name:20} ~ '{ref}' (ratio {ratio:.2f}), "
                      f"not found on PyPI -> likely typosquat")
                suspicious.append((name, ref, ratio))
            else:
                print(f"  review    {name:20} ~ '{ref}' (ratio {ratio:.2f}), "
                      f"exists on PyPI -> check popularity manually")
        else:
            print(f"  OK        {name:20} (no close match, ratio {ratio:.2f})")

    print()
    if suspicious:
        print("=" * 60)
        print("TYPOSQUATTING DETECTED - failing the build:")
        for name, ref, ratio in suspicious:
            print(f"  '{name}' looks like '{ref}' (similarity {ratio:.2f})")
        print("=" * 60)
        sys.exit(1)

    print("No typosquatting detected. All dependencies look clean.")
    sys.exit(0)


if __name__ == "__main__":
    main()