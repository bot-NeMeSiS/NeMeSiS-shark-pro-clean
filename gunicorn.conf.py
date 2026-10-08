"""Keep one process and the existing timeout; let navigation run beside Cron.

No extra scheduler or service: context-local request budgets and SQLite
connections stay separate for each request. CLI settings remain authoritative.
"""
worker_class = 'gthread'
threads = 2


def post_worker_init(worker):
    """Compile the initial client shell before accepting traffic, without rendering."""
    app = worker.wsgi
    for name in (
        'home.html', 'base.html', 'components/v936_product.html',
        'components/v933_ui.html', 'components/v937_sports_lifecycle.html',
        'components/v933_shells.html', 'partials/brand_logo.html',
        'components/navigation_contracts.html', 'components/v933_navigation.html',
        'components/app_navigation.html',
    ):
        app.jinja_env.get_template(name)
