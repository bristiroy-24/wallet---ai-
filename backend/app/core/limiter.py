"""
app/core/limiter.py
────────────────────
Shared SlowAPI rate limiter instance.

Uses in-memory storage — suitable for a single-process server.
For multi-process / multi-instance deployments, swap storage to
Redis: storage_uri="redis://localhost:6379"

Rate limits applied:
  - POST /auth/login    → 10 requests / minute  per IP
  - POST /auth/register → 5  requests / minute  per IP

These thresholds stop brute-force and credential-stuffing attacks
while allowing normal interactive usage.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# get_remote_address extracts the client IP from the request.
# Behind a reverse proxy, set X-Forwarded-For and use
# slowapi.util.get_ipaddr instead.
limiter = Limiter(key_func=get_remote_address)
