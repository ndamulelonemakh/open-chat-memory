import importlib.metadata

try:
    __version__ = importlib.metadata.version("openchatmemory")
except importlib.metadata.PackageNotFoundError:
    # Fallback for development/editable installs before first install
    __version__ = "0.1.0+dev"

SCHEMA_VERSION = "0.1.0"

__all__ = ["__version__", "SCHEMA_VERSION"]
