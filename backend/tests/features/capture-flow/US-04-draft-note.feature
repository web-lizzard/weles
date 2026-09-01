Feature: Draft note from conversation

  @capture-flow @AC-08
  Scenario: The agent produces a draft note when the user signals they are done
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    When the user says "The client sends SYN and the server replies SYN-ACK"
    And the user says "that's all"
    Then the draft note has a topic, body, and at least one tag

  @capture-flow @AC-09
  Scenario: The drafted topic can be more specific than the session topic
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    When the user says "The client sends SYN and the server replies SYN-ACK"
    And the user says "that's all"
    Then the drafted topic label differs from the session topic
