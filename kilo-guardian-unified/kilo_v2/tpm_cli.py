#!/usr/bin/env python3
"""
TPM Secret Management CLI

Command-line interface for managing TPM-sealed secrets.
Use this during initial appliance setup to seal credentials.

Usage:
    python -m kilo_v2.tpm_cli status         # Check TPM status
    python -m kilo_v2.tpm_cli seal           # Seal current credentials
    python -m kilo_v2.tpm_cli unseal         # Show unsealed credentials
    python -m kilo_v2.tpm_cli reseal         # Reseal after system update
    python -m kilo_v2.tpm_cli list           # List sealed secrets
"""

import argparse
import logging
import os
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def cmd_status(args):
    """Check TPM availability and status."""
    from kilo_v2.credential_manager import CredentialManager
    from kilo_v2.tpm_secrets import TPMSecretManager, TPMState

    print("=" * 50)
    print("TPM Secret Management Status")
    print("=" * 50)

    # Check TPM hardware
    tpm = TPMSecretManager()
    state = tpm.check_tpm_state()

    print(f"\nTPM State: {state.value}")

    if state == TPMState.AVAILABLE:
        print("✅ TPM 2.0 is available and accessible")

        # Read PCR values
        pcrs = tpm.get_pcr_values()
        if pcrs:
            print(f"\nPCR Values (policy: sha256:{tpm.pcrs}):")
            for idx, val in sorted(pcrs.items()):
                print(f"  PCR {idx}: {val[:20]}...")
    elif state == TPMState.NOT_PRESENT:
        print("⚠️  No TPM hardware detected")
        print("   Fallback encrypted storage will be used")
    elif state == TPMState.ACCESS_DENIED:
        print("❌ TPM access denied")
        print("   Check user permissions (needs access to /dev/tpm0)")
    elif state == TPMState.NOT_INITIALIZED:
        print("⚠️  tpm2-tools not installed")
        print("   Install with: nix-env -iA nixos.tpm2-tools")
    else:
        print(f"❌ TPM error: {state.value}")

    # List sealed secrets
    secrets = tpm.list_secrets()
    print(f"\nSealed Secrets: {len(secrets)}")
    for name in secrets:
        print(f"  - {name}")

    # Check credential manager
    print("\n" + "-" * 50)
    os.environ["USE_TPM_SECRETS"] = "1"
    cm = CredentialManager(use_tpm=True)
    print(f"Credential Manager TPM Enabled: {cm.tpm_enabled}")
    print(f"Credential Manager TPM Available: {cm.tpm_available}")
    print("=" * 50)


def cmd_seal(args):
    """Seal credentials to TPM."""
    from kilo_v2.credential_manager import CredentialManager

    print("=" * 50)
    print("Sealing Credentials to TPM")
    print("=" * 50)

    os.environ["USE_TPM_SECRETS"] = "1"
    cm = CredentialManager(use_tpm=True)

    if not cm._tpm_manager:
        print("❌ TPM manager not available")
        return 1

    # Load current credentials
    creds = cm.load()
    cm.log_status()

    print("\nSealing credentials...")
    if args.keys:
        keys = [k.upper() for k in args.keys]
    else:
        keys = None  # Seal all sealable keys

    results = cm.seal_to_tpm(keys)

    print("\nResults:")
    for key, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {key}")

    success_count = sum(1 for s in results.values() if s)
    print(f"\nSealed {success_count}/{len(results)} credentials")

    return 0 if all(results.values()) else 1


def cmd_unseal(args):
    """Show unsealed credentials (for verification)."""
    from kilo_v2.credential_manager import CredentialManager

    print("=" * 50)
    print("Unsealed Credentials (from TPM)")
    print("=" * 50)

    os.environ["USE_TPM_SECRETS"] = "1"
    cm = CredentialManager(use_tpm=True)

    if not cm._tpm_manager:
        print("❌ TPM manager not available")
        return 1

    results = cm.unseal_from_tpm()

    if not results:
        print("No sealed credentials found")
        return 0

    print("\nUnsealed values:")
    for key, value in results.items():
        # Mask sensitive values
        if len(value) > 8:
            masked = value[:4] + "****" + value[-4:]
        else:
            masked = "****"
        print(f"  {key}: {masked}")

    return 0


def cmd_reseal(args):
    """Reseal all credentials with current PCR values."""
    from kilo_v2.credential_manager import CredentialManager

    print("=" * 50)
    print("Resealing Credentials")
    print("=" * 50)
    print("")
    print("⚠️  This will reseal all credentials with current PCR values.")
    print("   Run this after a NixOS configuration update.")
    print("")

    if not args.force:
        response = input("Continue? [y/N] ")
        if response.lower() != "y":
            print("Cancelled")
            return 0

    os.environ["USE_TPM_SECRETS"] = "1"
    cm = CredentialManager(use_tpm=True)

    if not cm._tpm_manager:
        print("❌ TPM manager not available")
        return 1

    results = cm.reseal_all()

    print("\nResults:")
    for name, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {name}")

    return 0 if all(results.values()) else 1


def cmd_list(args):
    """List all sealed secrets."""
    import json

    from kilo_v2.tpm_secrets import TPMSecretManager

    tpm = TPMSecretManager()
    secrets = tpm.list_secrets()

    if not secrets:
        print("No sealed secrets found")
        return 0

    print(f"Sealed Secrets ({len(secrets)}):")
    print("-" * 40)

    for name in sorted(secrets):
        metadata_file = tpm.secrets_dir / name / "metadata.json"
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text())
            method = metadata.get("method", "unknown")
            created = metadata.get("created_at", "unknown")
            pcrs = metadata.get("pcrs", "N/A")
            print(f"  {name}")
            print(f"    Method: {method}")
            print(f"    Created: {created}")
            if method == "tpm":
                print(f"    PCRs: {pcrs}")
        else:
            print(f"  {name} (no metadata)")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="TPM Secret Management CLI for Bastion AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status           Check TPM availability
  %(prog)s seal             Seal all credentials
  %(prog)s seal -k KILO_API_KEY GEMINI_API_KEY
                            Seal specific credentials
  %(prog)s unseal           Verify sealed credentials
  %(prog)s reseal           Reseal after system update
  %(prog)s list             List sealed secrets
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # status
    status_parser = subparsers.add_parser("status", help="Check TPM status")
    status_parser.set_defaults(func=cmd_status)

    # seal
    seal_parser = subparsers.add_parser("seal", help="Seal credentials to TPM")
    seal_parser.add_argument(
        "-k",
        "--keys",
        nargs="+",
        help="Specific credential keys to seal (default: all)",
    )
    seal_parser.set_defaults(func=cmd_seal)

    # unseal
    unseal_parser = subparsers.add_parser("unseal", help="Show unsealed credentials")
    unseal_parser.set_defaults(func=cmd_unseal)

    # reseal
    reseal_parser = subparsers.add_parser("reseal", help="Reseal after system update")
    reseal_parser.add_argument(
        "-f", "--force", action="store_true", help="Skip confirmation prompt"
    )
    reseal_parser.set_defaults(func=cmd_reseal)

    # list
    list_parser = subparsers.add_parser("list", help="List sealed secrets")
    list_parser.set_defaults(func=cmd_list)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
