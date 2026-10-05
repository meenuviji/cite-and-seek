scenario: Security review flags the payment webhook endpoint as inconsistent with the rest of the API
real_file: app/api/payments.py
real_function: handle_payment_webhook
real_observable_behavior: >
  Every other endpoint in the API (cart, orders, /payments POST, /auth/me)
  declares current_user: User = Depends(get_current_user) as a parameter.
  handle_payment_webhook, mapped to POST /webhooks, has no such dependency
  and takes only the request body and a database session.
hypothetical_situation: >
  During an internal review, an engineer new to the codebase asks why the
  /webhooks endpoint doesn't require a bearer token like every other
  endpoint, and whether this was an oversight.
expected_evidence:
  - code/api/payments.py
expected_answer: >
  This matches the current implementation: /webhooks is the only endpoint
  without a get_current_user dependency. The corpus does not contain any
  comment, test, or documentation explaining this design choice or
  describing an alternative verification mechanism (such as a webhook
  signature check) for this endpoint, so whether it is an intentional
  design decision or an oversight cannot be determined from the corpus
  alone — only the fact of the inconsistency can be confirmed.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
