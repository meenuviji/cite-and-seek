scenario: Rate-limited login error reports a "wait time" that doesn't match the configured window
real_file: app/rate_limiter.py
real_function: rate_limit_login
real_observable_behavior: >
  rate_limit_login increments a Redis counter and, on first increment,
  sets its expiry to settings.rate_limit_seconds. When the count exceeds
  settings.rate_limit_times, it fetches the key's current ttl. If that ttl
  comes back negative (Redis convention for "no expiry set" or "key
  missing"), the code falls back to using settings.rate_limit_seconds as
  the reported wait time instead of the actual ttl.
hypothetical_situation: >
  A user is rate-limited and the error message reports a "try again in N
  seconds" value. An engineer asks under what circumstances that reported
  N could be the full configured window (e.g. 60s) rather than a
  countdown reflecting how much time is actually left.
expected_evidence:
  - code/rate_limiter.py
expected_answer: >
  This matches the current implementation: if the TTL lookup on the rate
  limit key returns a negative value (ttl < 0), the code does not treat
  that as an error — it falls back to reporting the full
  rate_limit_seconds value rather than a remaining-time countdown. The
  corpus does not include a test exercising this fallback branch
  specifically, so it is confirmed by code inspection only, not by test
  evidence.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
