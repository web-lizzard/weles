Feature: Coverage wrap-up signal

  @capture-flow @AC-05
  Scenario: The agent signals when the topic seems fully covered
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    And the confidence assessment reports full coverage
    When the user says "I think we've covered TCP thoroughly"
    Then the done event coverage confidence is fully covered

  @capture-flow @AC-06
  Scenario: The conversation continues after a full-coverage signal
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    And the confidence assessment reports full coverage
    When the user says "I think we've covered TCP thoroughly"
    And the user says "One more thing about retransmission"
    Then the follow-up message succeeds with a done event
