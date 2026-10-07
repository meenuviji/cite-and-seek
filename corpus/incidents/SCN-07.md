scenario: New engineer's local database is missing the payments table after a fresh clone
hypothetical_situation: >
  A new engineer clones the repository, runs a database setup step that
  only applies the first migration file they find, and then gets a
  "no such table: payments" error when hitting the payments endpoints.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
