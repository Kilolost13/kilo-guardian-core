"""
Printer Manager Plugin for Kilo Guardian
Discovers and manages household printers, enables printing from AI.
"""

import os
import platform
import subprocess
from typing import Dict, List, Optional

from plugins.base_plugin import BasePlugin


class PrinterManager(BasePlugin):
    """
    Printer management plugin for Kilo Guardian.
    Discovers local and network printers, manages print jobs.
    """

    def __init__(self):
        super().__init__()
        self.system = platform.system()
        self.default_printer = None
        self._discover_printers()

    def _discover_printers(self):
        """Discover available printers on the system."""
        try:
            if self.system == "Linux":
                # Use lpstat to discover CUPS printers
                result = subprocess.run(
                    ["lpstat", "-p", "-d"], capture_output=True, text=True, timeout=5
                )

                if result.returncode == 0:
                    # Parse default printer
                    for line in result.stdout.split("\n"):
                        if "system default" in line.lower():
                            parts = line.split()
                            if len(parts) > 3:
                                self.default_printer = parts[3]

            elif self.system == "Darwin":  # macOS
                result = subprocess.run(
                    ["lpstat", "-p", "-d"], capture_output=True, text=True, timeout=5
                )

                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if "system default" in line.lower():
                            parts = line.split()
                            if len(parts) > 3:
                                self.default_printer = parts[3]

            elif self.system == "Windows":
                # Use PowerShell to get default printer
                result = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        "Get-CimInstance -ClassName Win32_Printer | Where-Object { $_.Default -eq $true } | Select-Object -ExpandProperty Name",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    self.default_printer = result.stdout.strip()

        except Exception as e:
            print(f"Printer discovery error: {e}")

    def get_name(self) -> str:
        return "printer_manager"

    def get_keywords(self) -> list:
        return [
            "print",
            "printer",
            "printing",
            "hard copy",
            "paper",
            "print out",
            "print report",
            "physical copy",
        ]

    def run(self, query: str) -> dict:
        """Main execution method for printer queries."""
        query_lower = query.lower()

        try:
            # List printers
            if (
                "list" in query_lower
                or "show" in query_lower
                or "available" in query_lower
            ):
                return self._list_printers()

            # Set default printer
            if "default" in query_lower and "set" in query_lower:
                return self._handle_set_default(query)

            # Print test page
            if "test" in query_lower:
                return self._print_test_page()

            # Check printer status
            if "status" in query_lower:
                return self._get_printer_status()

            # Default: show help
            return self._get_help()

        except Exception as e:
            return {"type": "error", "tool": "printer_manager", "error": str(e)}

    def _list_printers(self) -> dict:
        """List all available printers."""
        printers = []

        try:
            if self.system == "Linux" or self.system == "Darwin":
                result = subprocess.run(
                    ["lpstat", "-p", "-d"], capture_output=True, text=True, timeout=5
                )

                if result.returncode == 0:
                    current_printer = None
                    for line in result.stdout.split("\n"):
                        if line.startswith("printer"):
                            parts = line.split()
                            if len(parts) >= 2:
                                printer_name = parts[1]
                                status = "idle" if "idle" in line else "unknown"
                                is_default = printer_name == self.default_printer

                                printers.append(
                                    {
                                        "name": printer_name,
                                        "status": status,
                                        "default": is_default,
                                        "type": "CUPS",
                                    }
                                )

            elif self.system == "Windows":
                result = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        "Get-CimInstance -ClassName Win32_Printer | Select-Object Name, PrinterStatus, Default | ConvertTo-Json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    import json

                    printer_data = json.loads(result.stdout)
                    if not isinstance(printer_data, list):
                        printer_data = [printer_data]

                    for p in printer_data:
                        printers.append(
                            {
                                "name": p.get("Name", "Unknown"),
                                "status": (
                                    "idle" if p.get("PrinterStatus") == 3 else "unknown"
                                ),
                                "default": p.get("Default", False),
                                "type": "Windows",
                            }
                        )

        except Exception as e:
            print(f"Error listing printers: {e}")

        return {
            "type": "printer_list",
            "tool": "printer_manager",
            "printers": printers,
            "default_printer": self.default_printer,
            "system": self.system,
            "count": len(printers),
        }

    def _get_printer_status(self) -> dict:
        """Get status of default printer."""
        if not self.default_printer:
            return {
                "type": "printer_status",
                "tool": "printer_manager",
                "message": "No default printer configured",
                "status": "no_printer",
            }

        try:
            if self.system == "Linux" or self.system == "Darwin":
                result = subprocess.run(
                    ["lpstat", "-p", self.default_printer],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    output = result.stdout.lower()
                    status = (
                        "idle"
                        if "idle" in output
                        else "busy" if "printing" in output else "unknown"
                    )

                    return {
                        "type": "printer_status",
                        "tool": "printer_manager",
                        "printer": self.default_printer,
                        "status": status,
                        "raw_output": result.stdout,
                    }

            elif self.system == "Windows":
                result = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        f"Get-CimInstance -ClassName Win32_Printer | Where-Object {{ $_.Name -eq '{self.default_printer}' }} | Select-Object PrinterStatus | ConvertTo-Json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    import json

                    data = json.loads(result.stdout)
                    status_code = data.get("PrinterStatus", 0)
                    status = (
                        "idle"
                        if status_code == 3
                        else "busy" if status_code == 4 else "unknown"
                    )

                    return {
                        "type": "printer_status",
                        "tool": "printer_manager",
                        "printer": self.default_printer,
                        "status": status,
                        "status_code": status_code,
                    }

        except Exception as e:
            return {
                "type": "printer_status",
                "tool": "printer_manager",
                "error": str(e),
                "status": "error",
            }

        return {
            "type": "printer_status",
            "tool": "printer_manager",
            "message": "Could not determine printer status",
            "status": "unknown",
        }

    def _print_test_page(self) -> dict:
        """Print a test page to default printer."""
        if not self.default_printer:
            return {
                "type": "print_result",
                "tool": "printer_manager",
                "success": False,
                "message": "No default printer configured",
            }

        try:
            # Create a simple test page
            test_content = f"""
            ═══════════════════════════════════════════════
                        KILO GUARDIAN TEST PAGE
            ═══════════════════════════════════════════════
            
            Printer: {self.default_printer}
            System: {self.system}
            
            This is a test page generated by Kilo Guardian's
            Printer Manager plugin.
            
            If you can read this, your printer is working
            correctly and ready for use with Bastion AI.
            
            ═══════════════════════════════════════════════
            """

            # Create temp file
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(test_content)
                temp_file = f.name

            # Send to printer
            if self.system == "Linux" or self.system == "Darwin":
                result = subprocess.run(
                    ["lpr", "-P", self.default_printer, temp_file],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                success = result.returncode == 0

            elif self.system == "Windows":
                result = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        f"Get-Content '{temp_file}' | Out-Printer -Name '{self.default_printer}'",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                success = result.returncode == 0
            else:
                success = False

            # Clean up
            try:
                os.unlink(temp_file)
            except:
                pass

            return {
                "type": "print_result",
                "tool": "printer_manager",
                "success": success,
                "message": (
                    "Test page sent to printer"
                    if success
                    else "Failed to send test page"
                ),
                "printer": self.default_printer,
            }

        except Exception as e:
            return {
                "type": "print_result",
                "tool": "printer_manager",
                "success": False,
                "error": str(e),
            }

    def print_document(
        self, content: str, title: str = "Kilo Guardian Document"
    ) -> bool:
        """
        Print a document to the default printer.
        This method can be called by other plugins or the AI.
        """
        if not self.default_printer:
            return False

        try:
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(f"{'='*60}\n")
                f.write(f"  {title}\n")
                f.write(f"{'='*60}\n\n")
                f.write(content)
                f.write(f"\n\n{'='*60}\n")
                f.write(f"Printed by: Kilo Guardian - Bastion AI\n")
                f.write(f"{'='*60}\n")
                temp_file = f.name

            if self.system == "Linux" or self.system == "Darwin":
                result = subprocess.run(
                    ["lpr", "-P", self.default_printer, temp_file],
                    capture_output=True,
                    timeout=10,
                )
                success = result.returncode == 0

            elif self.system == "Windows":
                result = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        f"Get-Content '{temp_file}' | Out-Printer -Name '{self.default_printer}'",
                    ],
                    capture_output=True,
                    timeout=10,
                )
                success = result.returncode == 0
            else:
                success = False

            try:
                os.unlink(temp_file)
            except:
                pass

            return success

        except Exception as e:
            print(f"Print error: {e}")
            return False

    def _handle_set_default(self, query: str) -> dict:
        """Handle setting default printer."""
        return {
            "type": "interactive_form",
            "tool": "printer_manager",
            "form": {
                "title": "Set Default Printer",
                "fields": [
                    {
                        "name": "printer_name",
                        "type": "text",
                        "label": "Printer Name",
                        "required": True,
                        "placeholder": "Enter printer name from list",
                    }
                ],
            },
            "message": "Enter the name of the printer to set as default",
        }

    def set_default_printer(self, printer_name: str) -> bool:
        """Set the default printer."""
        try:
            if self.system == "Linux" or self.system == "Darwin":
                result = subprocess.run(
                    ["lpoptions", "-d", printer_name], capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    self.default_printer = printer_name
                    return True

            elif self.system == "Windows":
                result = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        f"(Get-CimInstance -ClassName Win32_Printer | Where-Object {{ $_.Name -eq '{printer_name}' }}).SetDefaultPrinter()",
                    ],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    self.default_printer = printer_name
                    return True

        except Exception as e:
            print(f"Error setting default printer: {e}")

        return False

    def _get_help(self) -> dict:
        """Return help information."""
        return {
            "type": "printer_help",
            "tool": "printer_manager",
            "content": {
                "message": "Printer Manager - Control household printers from Bastion AI",
                "commands": [
                    "list printers - Show all available printers",
                    "printer status - Check default printer status",
                    "print test page - Send a test page to default printer",
                    "set default printer - Change default printer",
                ],
                "features": [
                    "🖨️ Automatic printer discovery",
                    "📄 Print reports, grocery lists, and documents",
                    "🔧 Manage multiple printers",
                    "✅ Cross-platform support (Linux, macOS, Windows)",
                ],
                "default_printer": self.default_printer or "None configured",
                "system": self.system,
            },
        }

    def execute(self, query: str) -> dict:
        """Execute method for reasoning engine."""
        return self.run(query)
