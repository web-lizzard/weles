Feature: The list says what happened to each note

  @distill-flow @AC-08
  Scenario: Each note exposes topic, distillation state, and live card count
    Given a running notes backend
    And a ready note titled "TCP handshakes" with 2 live cards
    When the user requests the note list
    Then that note appears in the list with topic, status, and card count

  @distill-flow @AC-09
  Scenario: The list distinguishes generating, finished-with-zero, and failed notes
    Given a running notes backend
    And a generating note with topic "In progress"
    And a ready note with topic "Empty result" and zero live cards
    And a failed note with topic "Broken run"
    When the user requests the note list
    Then the list exposes generating, zero-card-ready, and failed states

  @distill-flow @AC-10
  Scenario: Notes appear most recently touched first
    Given a running notes backend
    And an older note with topic "Older topic"
    And a newer note with topic "Newer topic" touched more recently than the older note
    When the user requests the note list
    Then the note list is ordered with the most recently touched note first
