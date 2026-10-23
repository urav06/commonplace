"""Running the library's outside tools: Calibre's, poppler's, pandoc, and the Vision reader."""

import os
import subprocess
import sys
from typing import Final

QUIET: Final = os.environ | {"PYTHON_COLORS": "0", "NO_COLOR": "1"}  # plain error text from Calibre's tools


def run(*args: str, input: str | None = None) -> str:
    """The tool's output. A missing tool stops the run; a failing one raises with its last line of complaint."""
    try:
        return subprocess.run(args, input=input, capture_output=True, text=True, check=True, env=QUIET).stdout
    except FileNotFoundError:
        sys.exit(f"{args[0]} is not installed")
    except subprocess.CalledProcessError as error:
        lines = (error.stderr or error.stdout).strip().splitlines()
        raise RuntimeError(lines[-1] if lines else f"{args[0]} failed") from None
