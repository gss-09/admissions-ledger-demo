"""Data access layer — one module per domain. ALL SQL lives here; nothing else
in the app runs SQL. Every value is bound as a parameter (``?`` placeholders,
rewritten to ``%s`` by ``app.db._Conn``); the only dynamic SQL is whitelisted
column names."""
