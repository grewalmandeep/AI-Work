"""Write exception tracebacks to a file so the UI can show them when errors are caught in clients."""
import os
import traceback
import logging

logger = logging.getLogger(__name__)
_PATH = None


def get_traceback_path() -> str:
    """Return path to .last_traceback.txt in project root (parent of utils/)."""
    global _PATH
    if _PATH is None:
        _PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".last_traceback.txt")
    return _PATH


def write_traceback(exc: BaseException) -> None:
    """Write the current exception's traceback to .last_traceback.txt in project root."""
    tb = traceback.format_exc()
    if not tb.strip():
        tb = f"{type(exc).__name__}: {exc}\n"
    path = get_traceback_path()
    try:
        with open(path, "w") as f:
            f.write(tb)
        logger.info(f"Traceback written to {path}")
    except Exception as e:
        logger.warning(f"Could not write traceback to {path}: {e}")
    # Also write to cwd if different
    cwd_path = os.path.join(os.getcwd(), ".last_traceback.txt")
    if os.path.abspath(cwd_path) != os.path.abspath(path):
        try:
            with open(cwd_path, "w") as f:
                f.write(tb)
        except Exception:
            pass


def read_traceback() -> str:
    """Read traceback from project root or cwd. Returns empty string if not found."""
    for p in [get_traceback_path(), os.path.join(os.getcwd(), ".last_traceback.txt")]:
        try:
            if os.path.isfile(p):
                with open(p, "r") as f:
                    return f.read()
        except Exception:
            continue
    return ""
