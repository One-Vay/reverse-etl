"""Connector layer: pluggable integrations with external data systems.

This package is intentionally isolated from the rest of the application —
nothing in here imports from ``app.features`` or ``app.core``. Connectors
know how to talk to a source or destination system; they know nothing
about sources, destinations, mappings, or syncs as *business* concepts.
That separation is what lets `ConnectorFactory` and the connectors
themselves be unit-tested without a database, and lets new connector
types be added without touching any feature code.
"""
