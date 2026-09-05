Feature: Never a card the note doesn't support

  @distill-flow @AC-05
  Scenario: Every live card's quote resolves within its note
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    When the user says "The client sends SYN and the server replies SYN-ACK"
    And the user says "that's all"
    And the user approves the draft
    And the distill worker drains the outbox once
    Then every live card's quote resolves within the held note

  @distill-flow @AC-06
  Scenario: A card whose quoted fragment is absent from its note never reaches the user
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    When the user says "The client sends SYN and the server replies SYN-ACK"
    And the user says "that's all"
    And the user approves the draft
    And the distill worker drains the outbox once
    Then the held note has a discarded card whose reason is ungrounded
    And that discarded card does not appear among the held note's live cards
