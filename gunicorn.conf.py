"""Keep one process and the existing timeout; let navigation run beside Cron.

No extra scheduler or service: context-local request budgets and SQLite
connections stay separate for each request. CLI settings remain authoritative.
"""
worker_class = 'gthread'
threads = 2
