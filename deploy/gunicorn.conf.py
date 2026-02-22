import multiprocessing

# Gunicorn configuration file
# https://docs.gunicorn.org/en/stable/settings.html

# Bind to a socket or port
bind = "127.0.0.1:8000"

# Number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# The type of workers to use
worker_class = "sync"

# Maximum number of requests a worker will process before restarting
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Django WSGI application path
wsgi_app = "remedial.wsgi:application"
