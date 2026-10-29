"""Compatibility entry point; implementation: pitwall/dashboard/components.py."""
if __name__ == "__main__":
    import runpy
    runpy.run_module("pitwall.dashboard.components", run_name="__main__")
else:
    import sys
    from importlib import import_module
    _implementation = import_module("pitwall.dashboard.components")
    sys.modules[__name__] = _implementation
    globals().update(vars(_implementation))
