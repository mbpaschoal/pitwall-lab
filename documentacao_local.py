"""Compatibility entry point; implementation: pitwall/publishing/documentation.py."""
if __name__ == "__main__":
    import runpy
    runpy.run_module("pitwall.publishing.documentation", run_name="__main__")
else:
    import sys
    from importlib import import_module
    _implementation = import_module("pitwall.publishing.documentation")
    sys.modules[__name__] = _implementation
    globals().update(vars(_implementation))
