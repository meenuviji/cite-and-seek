scenario: Order stuck in PENDING after a payment failure
real_file: app/services/payment_service.py
real_function: process_mock_webhook
real_observable_behavior: >
  When a webhook call sets a payment's status to PAID, the function also
  sets order.status = OrderStatus.PAID. When a webhook call sets the
  payment's status to FAILED, only the Payment record is updated —
  there is no corresponding branch that changes order.status. This is
  independently confirmed by tests/test_payments.py::
  test_webhook_marks_payment_failed_without_paying_order, which asserts
  the order remains "PENDING" after a FAILED webhook.
hypothetical_situation: >
  A support engineer is asked why a customer's order has shown "PENDING"
  for several days after the customer's card was declined and the
  payment provider's webhook reported the failure.
expected_evidence:
  - code/services/payment_service.py
  - tests/test_payments.py
expected_answer: >
  This matches the current implementation: process_mock_webhook only
  updates order.status when the new payment status is PAID. A FAILED
  webhook updates only the Payment row. The order therefore remains in
  whatever status it had before the webhook call (typically PENDING)
  unless a separate order status-update call is made.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
