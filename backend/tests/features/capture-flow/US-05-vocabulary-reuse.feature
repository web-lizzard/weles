Feature: Reuse existing topics and tags across capture sessions

  @capture-flow @AC-10
  Scenario: A repeated conversation reuses the existing topic and tags
    Given a running capture backend
    When the user starts and completes a capture session about "How TCP handshakes work" explaining "The client sends SYN and the server replies SYN-ACK"
    And the user starts and completes another capture session about "How TCP handshakes work" explaining "The client sends SYN and the server replies SYN-ACK"
    Then the second session's drafted topic is marked as reused
    And the second session's drafted tags are all marked as reused

  @capture-flow @AC-11
  Scenario: A first-ever tag is shown to the user as newly minted
    Given a running capture backend
    When the user starts and completes a capture session about "How TCP handshakes work" explaining "The client sends SYN and the server replies SYN-ACK"
    Then the drafted topic is marked as newly minted
    And the drafted tags are all marked as newly minted
