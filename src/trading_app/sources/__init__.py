"""Data source adapters.

Every source returns validated ``Bar`` objects or, for ``documents``, a
stored PDF file. Raw dicts never leave an adapter module — otherwise input
validation moves to the caller, and there it gets forgotten.
"""
