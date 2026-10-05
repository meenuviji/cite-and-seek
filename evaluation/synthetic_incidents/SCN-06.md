scenario: Two simultaneous checkouts for the last unit of a product
real_file: app/services/order_service.py, app/services/cart_service.py
real_function: create_order_from_cart, add_item_to_cart
real_observable_behavior: >
  Both create_order_from_cart and add_item_to_cart follow the same pattern:
  read product.stock, compare it against the requested quantity, raise an
  error if insufficient, and otherwise decrement/use it within the same
  database session. Neither function uses an explicit row lock (e.g.
  SELECT ... FOR UPDATE), a database-level check constraint on stock, or
  an optimistic-concurrency version column.
hypothetical_situation: >
  Two customers submit checkout requests for the same product at nearly
  the same time, when only one unit remains in stock. A reviewer asks
  whether the system guarantees that only one of the two orders can
  succeed.
expected_evidence:
  - code/services/order_service.py
  - code/services/cart_service.py
expected_answer: >
  The corpus does not contain any explicit concurrency-control mechanism
  (row locking, unique constraint, or optimistic locking) around the
  stock check-and-decrement logic in either function. Based on the code
  alone, whether two near-simultaneous requests could both pass the stock
  check before either commit depends on the database engine's default
  transaction isolation behavior, which is not something this corpus
  documents or tests. This is a genuine gap in what can be confirmed from
  the corpus, not a confirmed bug — the appropriate answer here is that
  the system does not implement any observable safeguard, and no test in
  the corpus exercises concurrent requests.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
