Feature: Approve the draft into the outbox

  @capture-flow @AC-14
  Scenario: Nothing reaches the outbox without explicit approval
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    When the user says "The client sends SYN and the server replies SYN-ACK"
    And the user says "that's all"
    Then no envelope has been queued to the outbox
    When the user approves the draft
    Then exactly one envelope has been queued to the outbox

  @capture-flow @AC-15
  Scenario: Approval sends the note and ends the session
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    When the user says "The client sends SYN and the server replies SYN-ACK"
    And the user says "that's all"
    And the user approves the draft
    Then the approval response reports the note as approved
    And the capture session is closed
