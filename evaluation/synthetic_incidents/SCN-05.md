scenario: Customer service cannot cancel a delivered order, or reopen a cancelled one
real_file: app/services/order_service.py
real_function: validate_transition
real_observable_behavior: >
  validate_transition contains explicit early checks: if current_status is
  CANCELLED, any further transition raises 400 "Cannot move a cancelled
  order to another status"; if current_status is DELIVERED and the
  requested new_status is CANCELLED, it raises 400 "Cannot cancel a
  delivered order". Both checks run before the general ALLOWED_TRANSITIONS
  lookup.
hypothetical_situation: >
  A customer service agent tries to cancel an order that has already been
  marked DELIVERED (customer wants a return), and separately tries to
  reactivate an order that was mistakenly CANCELLED.
expected_evidence:
  - code/services/order_service.py
expected_answer: >
  Both actions are blocked by design, per the current implementation.
  Attempting to cancel a DELIVERED order raises HTTP 400 with "Cannot
  cancel a delivered order." Attempting to move a CANCELLED order to any
  other status — including back to PENDING or PAID — raises HTTP 400 with
  "Cannot move a cancelled order to another status." The corpus contains
  no separate "return" or "reactivate" flow; these are terminal states as
  implemented.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
