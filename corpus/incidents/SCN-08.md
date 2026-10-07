scenario: Rate-limited login error reports a "wait time" that doesn't match the configured window
hypothetical_situation: >
  A user is rate-limited and the error message reports a "try again in N
  seconds" value. An engineer asks under what circumstances that reported
  N could be the full configured window (e.g. 60s) rather than a
  countdown reflecting how much time is actually left.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
