Feature: Reshape the draft before it is saved

  @capture-flow @AC-12
  Scenario: The draft is shown with a topic, body, and tags before anything is saved
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    When the user says "The client sends SYN and the server replies SYN-ACK"
    And the user says "that's all"
    Then the draft note has a topic, body, and at least one tag
    And no envelope has been queued to the outbox

  @capture-flow @AC-13
  Scenario: A described change yields a redraft on the same note
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    When the user says "The client sends SYN and the server replies SYN-ACK"
    And the user says "that's all"
    And the user says "Also mention the ACK step explicitly"
    And the user says "that's all"
    Then the redraft keeps the same note id as the first draft
    And the redrafted content differs from the first draft
