Feature: Cards without asking, and nothing is a fine answer

  @distill-flow @AC-03
  Scenario: Cards exist for a held note without the user asking for them
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    When the user says "The client sends SYN and the server replies SYN-ACK"
    And the user says "that's all"
    And the user approves the draft
    And the distill worker drains the outbox once
    Then the held note has at least one live card

  @distill-flow @AC-04
  Scenario: A note that yields no cards still ends completed
    Given a held note whose content fits in a single sentence
    When the distill worker drains the outbox once
    Then the held note's distillation is ready
    And the held note has zero live cards
