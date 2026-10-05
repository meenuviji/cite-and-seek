scenario: Customer reports never receiving confirmation after a successful payment
real_file: app/api/payments.py, app/services/notification_service.py
real_function: create_payment, handle_payment_webhook, write_order_notification
real_observable_behavior: >
  write_order_notification is called only from app/api/orders.py, for the
  ORDER_CREATED, ORDER_STATUS_UPDATED, and ORDER_CANCELLED events. Neither
  the payment-creation endpoint nor the webhook endpoint in
  app/api/payments.py imports or calls notification_service at all.
hypothetical_situation: >
  A customer says they paid for an order and their order status changed
  to PAID, but they never received any notification about the payment
  itself (only, if anything, the original order-created notification).
expected_evidence:
  - code/api/payments.py
  - code/services/notification_service.py
  - code/api/orders.py
expected_answer: >
  This matches the current implementation. No notification is generated
  anywhere in the payment flow — not on payment creation, and not on a
  webhook marking a payment PAID or FAILED. The only notifications the
  system produces are tied to order lifecycle events handled in
  app/api/orders.py (creation, status update, cancellation), which are
  separate code paths from the payment endpoints.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
