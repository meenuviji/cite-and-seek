scenario: Security review flags the payment webhook endpoint as inconsistent with the rest of the API
hypothetical_situation: >
  During an internal review, an engineer new to the codebase asks why the
  /webhooks endpoint doesn't require a bearer token like every other
  endpoint, and whether this was an oversight.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
