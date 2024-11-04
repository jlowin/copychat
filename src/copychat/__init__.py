"""Convert source code directories into markdown for LLM context."""


# --- Version ---

try:
    from ._version import version as __version__  # type: ignore
except ImportError:
    __version__ = "unknown"
