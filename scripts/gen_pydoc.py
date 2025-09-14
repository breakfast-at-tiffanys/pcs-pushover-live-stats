#!/usr/bin/env python3
"""Generate pydoc HTML for the pcs_pushover package.

Writes output into ./docs and creates a simple index.html that links to each
module's pydoc page.
"""

from __future__ import annotations

import html
import os
import pkgutil
import pydoc
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_NAME = "pcs_pushover"
PKG_DIR = ROOT / PKG_NAME
DOCS_DIR = ROOT / "docs"


def discover_modules(package_dir: Path, pkg_name: str) -> list[str]:
    """Return a sorted list of fully-qualified modules inside a package dir.

    Args:
        package_dir: Filesystem path to the package directory.
        pkg_name: The importable package name (e.g., "pcs_pushover").
    """
    modules: list[str] = [pkg_name]
    for _finder, name, _ispkg in pkgutil.walk_packages(
        [str(package_dir)], prefix=pkg_name + "."
    ):
        # Skip dunders or private modules
        short = name.split(".")[-1]
        if short.startswith("_"):
            continue
        modules.append(name)
    return sorted(modules)


def render_index(modules: list[str]) -> str:
    """Render a minimal index.html that links to each module page."""
    rows_html = "".join(
        f'<li><a href="{m}.html">{html.escape(m)}</a></li>' for m in modules
    )
    return f"""
<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Pydoc: {html.escape(PKG_NAME)}</title>
    <style>
      body {{
        font: 14px/1.45 -apple-system, BlinkMacSystemFont, Segoe UI, Roboto,
              Helvetica, Arial, sans-serif;
        margin: 2rem;
      }}
      code, pre {{
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      }}
    </style>
  </head>
  <body>
    <h1>Pydoc: {html.escape(PKG_NAME)}</h1>
    <p>
      Auto-generated documentation for the
      <code>{html.escape(PKG_NAME)}</code> package.
    </p>
    <ul>
      {rows_html}
    </ul>
  </body>
</html>
"""


def main() -> int:
    """Generate pydoc HTML into docs/ and write an index page."""
    sys.path.insert(0, str(ROOT))
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    modules = discover_modules(PKG_DIR, PKG_NAME)

    # Write pydoc files into docs directory
    cwd = os.getcwd()
    os.chdir(DOCS_DIR)
    try:
        for mod in modules:
            try:
                pydoc.writedoc(mod)
            except Exception as e:  # pragma: no cover - informational only
                print(f"Skipping {mod}: {e}")
    finally:
        os.chdir(cwd)

    # Render index.html
    (DOCS_DIR / "index.html").write_text(render_index(modules), encoding="utf-8")
    print(f"Wrote {len(modules)} module docs to {DOCS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
