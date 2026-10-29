"""Compatibility entry point; implementation: pitwall/dashboard/app.py."""
if __name__ == "__main__":
    from pitwall.dashboard.app import executar_app
    executar_app()
else:
    import sys
    from importlib import import_module
    _implementation = import_module("pitwall.dashboard.app")
    sys.modules[__name__] = _implementation
    globals().update(vars(_implementation))
