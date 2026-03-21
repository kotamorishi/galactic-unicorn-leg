"""Microdot - placeholder for the actual microdot web framework.

The real microdot.py should be downloaded from:
https://github.com/miguelgrinberg/microdot

This placeholder provides the interface so imports work during
PC-side testing. For device deployment, replace with the real file.

On CPython (testing), the real microdot can be installed via:
    pip install microdot
"""

try:
    from microdot import Microdot  # noqa: F401 - try real package first
except ImportError:
    # Minimal stub for import compatibility only.
    # Replace this file with the real microdot.py for production use.
    class _Request:
        def __init__(self):
            self.json = None
            self.method = "GET"
            self.path = "/"
            self.headers = {}

    class Microdot:
        def __init__(self):
            self.ctx = {}
            self._routes = {}

        def route(self, path, methods=None):
            def decorator(f):
                key = (path, tuple(methods or ["GET"]))
                self._routes[key] = f
                return f
            return decorator

        async def start_server(self, host="0.0.0.0", port=80):
            raise NotImplementedError(
                "This is a stub. Install real microdot: pip install microdot"
            )

        def run(self, host="0.0.0.0", port=80):
            raise NotImplementedError(
                "This is a stub. Install real microdot: pip install microdot"
            )
