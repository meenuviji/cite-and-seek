scenario: Invoice doesn't reflect an order's final status after it ships
real_file: app/api/orders.py
real_function: create_order, update_order_status, cancel_order
real_observable_behavior: >
  generate_invoice_file is scheduled as a background task only inside
  create_order, using the order's status at creation time (always
  PENDING). update_order_status and cancel_order only schedule
  write_order_notification as a background task; neither calls
  generate_invoice_file again.
hypothetical_situation: >
  A customer downloads their invoice after their order has been marked
  SHIPPED, and notices the invoice file still shows "PENDING" as the
  order status.
expected_evidence:
  - code/api/orders.py
  - code/services/invoice_service.py
expected_answer: >
  This matches the current implementation. The invoice file is generated
  exactly once, at order-creation time, capturing the order's status at
  that moment (PENDING). No code path regenerates or updates the invoice
  file when the order's status later changes via update_order_status or
  cancel_order — those only produce notification files, not invoice
  updates.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
