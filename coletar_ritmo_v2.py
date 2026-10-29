"""Compatibility entry point; implementation: pitwall/research/pace_collection_v2.py."""
if __name__ == "__main__":
    import runpy
    runpy.run_module("pitwall.research.pace_collection_v2", run_name="__main__")
else:
    import sys
    from importlib import import_module
    _implementation = import_module("pitwall.research.pace_collection_v2")
    sys.modules[__name__] = _implementation
    globals().update(vars(_implementation))
