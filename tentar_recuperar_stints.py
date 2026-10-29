"""Compatibility entry point; implementation: pitwall/data/stint_recovery.py."""
if __name__ == "__main__":
    import runpy
    runpy.run_module("pitwall.data.stint_recovery", run_name="__main__")
else:
    import sys
    from importlib import import_module
    _implementation = import_module("pitwall.data.stint_recovery")
    sys.modules[__name__] = _implementation
    globals().update(vars(_implementation))
