bind='127.0.0.1:8050'
workers=1
worker_class='gthread'
threads=4
timeout=120
graceful_timeout=30
accesslog='-'
errorlog='-'
# Nginx is the only trusted proxy and cannot be bypassed from the public network.
forwarded_allow_ips='127.0.0.1'
