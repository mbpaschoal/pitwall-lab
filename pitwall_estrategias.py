"""Compatibility entry point; implementation: pitwall/data/tyre_strategies.py."""
if __name__ == "__main__":
    import runpy
    runpy.run_module("pitwall.data.tyre_strategies", run_name="__main__")
else:
    import sys
    from importlib import import_module
    _implementation = import_module("pitwall.data.tyre_strategies")
    sys.modules[__name__] = _implementation
    globals().update(vars(_implementation))
