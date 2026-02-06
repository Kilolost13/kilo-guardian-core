"""Update service helper functions to centralize update logic for routes.

This file wraps update_manager operations and HTTP requests so routers can
call into a small, testable surface area.
"""

from pathlib import Path
from typing import Any, Dict

import requests


def check_for_updates(
    update_manager_module=None, requests_module=None
) -> Dict[str, Any]:
    update_manager_module = update_manager_module or __import__(
        "kilo_v2.update_manager", fromlist=["*"]
    )
    requests_module = requests_module or requests

    UPDATE_CHECK_URL = getattr(update_manager_module, "UPDATE_CHECK_URL", None)
    verify_manifest_signature = getattr(
        update_manager_module, "verify_manifest_signature", lambda m: True
    )

    version_file = Path(__file__).parent.parent / "VERSION"
    current_version = (
        version_file.read_text().strip() if version_file.exists() else "0.0.0"
    )

    resp = requests_module.get(UPDATE_CHECK_URL, timeout=10)
    resp.raise_for_status()
    manifest = resp.json()

    if not verify_manifest_signature(manifest):
        return {
            "error": "Update signature verification failed",
            "update_available": False,
        }

    latest_version = manifest.get("version", "0.0.0")
    update_available = latest_version > current_version
    return {
        "update_available": update_available,
        "current_version": current_version,
        "latest_version": latest_version,
        "release_date": manifest.get("release_date"),
        "changelog_url": manifest.get("changelog_url"),
    }


def download_update(
    download_dir: str = "/var/lib/kilo/updates",
    update_manager_module=None,
    requests_module=None,
) -> Dict[str, Any]:
    update_manager_module = update_manager_module or __import__(
        "kilo_v2.update_manager", fromlist=["*"]
    )
    requests_module = requests_module or requests
    UPDATE_CHECK_URL = getattr(update_manager_module, "UPDATE_CHECK_URL", None)
    verify_manifest_signature = getattr(
        update_manager_module, "verify_manifest_signature", lambda m: True
    )
    verify_iso_checksum = getattr(
        update_manager_module, "verify_iso_checksum", lambda p, sha: True
    )

    resp = requests_module.get(UPDATE_CHECK_URL, timeout=10)
    resp.raise_for_status()
    manifest = resp.json()
    if not verify_manifest_signature(manifest):
        raise ValueError("Signature verification failed")

    iso_url = manifest["iso_url"]
    iso_filename = f"nixos-kilo-{manifest['version']}.iso"
    download_dir_path = Path(download_dir)
    download_dir_path.mkdir(parents=True, exist_ok=True)
    iso_path = download_dir_path / iso_filename

    resp = requests_module.get(iso_url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(iso_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    if not verify_iso_checksum(str(iso_path), manifest["iso_sha256"]):
        iso_path.unlink()
        raise ValueError("ISO checksum verification failed")

    return {
        "success": True,
        "iso_path": str(iso_path),
        "version": manifest["version"],
    }


def apply_update(iso_path: str, update_manager_module=None) -> Dict[str, Any]:
    update_manager_module = update_manager_module or __import__(
        "kilo_v2.update_manager", fromlist=["*"]
    )
    apply_nixos_update = getattr(
        update_manager_module, "apply_nixos_update", lambda p: False
    )
    if not Path(iso_path).exists():
        raise FileNotFoundError("ISO file not found")
    success = apply_nixos_update(iso_path)
    if success:
        return {
            "success": True,
            "message": "Update applied successfully. Reboot to activate.",
        }
    raise RuntimeError("Update application failed")


def rollback_update(update_manager_module=None) -> Dict[str, Any]:
    update_manager_module = update_manager_module or __import__(
        "kilo_v2.update_manager", fromlist=["*"]
    )
    rollback_nixos_update = getattr(
        update_manager_module, "rollback_nixos_update", lambda: False
    )
    success = rollback_nixos_update()
    if success:
        return {"success": True, "message": "Rollback complete"}
    raise RuntimeError("Rollback failed")


def list_generations(update_manager_module=None) -> Dict[str, Any]:
    update_manager_module = update_manager_module or __import__(
        "kilo_v2.update_manager", fromlist=["*"]
    )
    list_nixos_generations = getattr(
        update_manager_module, "list_nixos_generations", lambda: []
    )
    generations = list_nixos_generations()
    return {"generations": generations}
