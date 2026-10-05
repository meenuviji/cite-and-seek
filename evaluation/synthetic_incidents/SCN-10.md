scenario: JWT tokens issued in a freshly cloned, unconfigured environment
real_file: app/config.py
real_function: Settings class definition
real_observable_behavior: >
  Settings.secret_key has a default value of the literal string
  "change-this-in-production", used unless overridden by a SECRET_KEY
  environment variable or .env entry. This default is used directly in
  jwt.encode/jwt.decode calls in auth_utils.py.
hypothetical_situation: >
  A developer runs the application immediately after cloning it, without
  creating a .env file, and asks what secret key is being used to sign
  JWT tokens in that state.
expected_evidence:
  - code/config.py
  - code/auth_utils.py
expected_answer: >
  In that state, the application uses the literal default value
  "change-this-in-production" as the JWT signing key, because no .env
  file or environment variable overrides Settings.secret_key. The
  corpus does not state whether this default is ever validated against
  or rejected at startup — there is no such check in app/config.py or
  app/main.py within the inspected corpus.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
