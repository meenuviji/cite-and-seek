scenario: Changing PRODUCT_CACHE_TTL in one place doesn't seem to change caching behavior
hypothetical_situation: >
  A developer changes product_cache_ttl in the Settings class (or assumes
  changing it there is sufficient) expecting the product cache duration to
  change, but observes no difference in caching behavior.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
