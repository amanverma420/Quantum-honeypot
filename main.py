"""Main Entry Point for the Quantum Honeypot System."""

import sys
from quantum_honeypot.cli import main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Default behavior if run without args: run benchmark, generate charts & PDF, and show status
        sys.argv.append("simulate")
    main()
