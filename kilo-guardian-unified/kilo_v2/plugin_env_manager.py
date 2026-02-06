#!/usr/bin/env python3
"""
Utility to create per-plugin virtual environments and install requirements specified
in a plugin manifest. This is a medium-term helper: it won't be invoked automatically
by PluginManager yet, but provides a CLI to create/update/remove per-plugin venvs.

Usage:
  python plugin_env_manager.py create path/to/plugin.json
  python plugin_env_manager.py update path/to/plugin.json
  python plugin_env_manager.py remove plugin_name

The manifest should include a "requirements" list, e.g.:
{
  "name": "test_api",
  "isolate": true,
  "requirements": ["requests>=2.28"]
}
"""

import json
import os
import subprocess
import sys
import venv
from pathlib import Path

PLUGIN_VENV_ROOT = Path(__file__).parent / "plugin_venvs"


def _create_venv(venv_path: Path):
    print(f"Creating venv at {venv_path}")
    builder = venv.EnvBuilder(with_pip=True)
    builder.create(str(venv_path))


def _install_requirements(venv_path: Path, reqs):
    if not reqs:
        print("No requirements to install.")
        return
    if os.name == "nt":
        py = venv_path / "Scripts" / "python.exe"
    else:
        py = venv_path / "bin" / "python"
    cmd = [str(py), "-m", "pip", "install", "--upgrade", "pip"]
    subprocess.check_call(cmd)
    cmd = [str(py), "-m", "pip", "install"] + reqs
    subprocess.check_call(cmd)


def create_or_update(manifest_path):
    p = Path(manifest_path)
    if not p.exists():
        print(f"Manifest not found: {manifest_path}")
        sys.exit(2)
    manifest = json.loads(p.read_text())
    name = manifest.get("name") or p.stem
    reqs = manifest.get("requirements", [])
    venv_dir = PLUGIN_VENV_ROOT / name
    venv_dir.parent.mkdir(parents=True, exist_ok=True)
    if not venv_dir.exists():
        _create_venv(venv_dir)
    _install_requirements(venv_dir, reqs)
    print(f"Plugin venv ready at: {venv_dir}")


def remove(name):
    venv_dir = PLUGIN_VENV_ROOT / name
    if not venv_dir.exists():
        print(f"Venv not found: {venv_dir}")
        return
    import shutil

    shutil.rmtree(venv_dir)
    print(f"Removed venv for {name}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    op = sys.argv[1]
    arg = sys.argv[2]
    if op in ("create", "update"):
        create_or_update(arg)
    elif op == "remove":
        remove(arg)
    else:
        print("Unknown operation")
        sys.exit(2)
