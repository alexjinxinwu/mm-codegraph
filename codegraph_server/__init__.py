"""codegraph-server — Python HTTP web app, depends on codegraph-core.

Exposes HTTP REST API for graph browsing and analysis.
Reuses QueryEngine and analyzer_compat from codegraph-core.
"""

from .app import app

__all__ = ["app"]