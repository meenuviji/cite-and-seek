scenario: Changing PRODUCT_CACHE_TTL in one place doesn't seem to change caching behavior
real_file: app/config.py, app/api/products.py
real_function: Settings (config.py), get_products / get_product (products.py)
real_observable_behavior: >
  app/config.py defines product_cache_ttl on the pydantic Settings object,
  loaded from the .env file via pydantic-settings. However, app/api/products.py
  does not reference settings.product_cache_ttl anywhere. Instead, it calls
  its own load_dotenv() and reads
  PRODUCT_CACHE_TTL = int(os.getenv("PRODUCT_CACHE_TTL", "60"))
  as a module-level constant, used directly in the redis_client.setex calls.
hypothetical_situation: >
  A developer changes product_cache_ttl in the Settings class (or assumes
  changing it there is sufficient) expecting the product cache duration to
  change, but observes no difference in caching behavior.
expected_evidence:
  - code/config.py
  - code/api/products.py
expected_answer: >
  This matches the current implementation. The two files implement separate
  configuration paths for what is conceptually the same setting: config.py's
  Settings.product_cache_ttl is never imported or used by products.py, which
  independently reads the PRODUCT_CACHE_TTL environment variable itself.
  Both default to 60, so this is not observable until someone changes only
  one of the two settings sources.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
