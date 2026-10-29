"""Compatibility entry point; implementation: pitwall/data/visual_catalog.py."""
if __name__ == "__main__":
    import runpy
    runpy.run_module("pitwall.data.visual_catalog", run_name="__main__")
else:
    import sys
    from importlib import import_module
    _implementation = import_module("pitwall.data.visual_catalog")
    sys.modules[__name__] = _implementation
    globals().update(vars(_implementation))
