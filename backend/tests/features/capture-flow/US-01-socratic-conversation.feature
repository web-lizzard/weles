Feature: Surface understanding gaps through conversation

  @capture-flow @AC-01
  Scenario: User starts a capture session by naming a topic
    Given a running capture backend
    When the user starts a capture session
    And the user names the topic "How TCP handshakes work"
    Then the session topic is set to "How TCP handshakes work"

  @capture-flow @AC-02
  Scenario: The agent asks follow-up questions rather than only recording
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    When the user says "I think the three-way handshake establishes a connection"
    Then the agent reply probes understanding with a follow-up question

  @capture-flow @AC-03
  Scenario: The agent gently indicates solid and shaky parts of the explanation
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    When the user says "The client sends SYN and the server replies SYN-ACK"
    Then the agent reply acknowledges what seems solid
    And the agent reply flags what seems shaky

  @capture-flow @AC-04
  Scenario: Follow-up questions concentrate on the shaky parts
    Given a running capture backend
    And the user has started a capture session with topic "How TCP handshakes work"
    When the user says "Then the client sends ACK to complete the handshake"
    Then the agent follow-up targets the shaky part of the latest user message
