Feature: Jump from a card to where it came from

  @distill-flow @AC-13
  Scenario: A live card's anchor resolves to a location within the held note
    Given a running notes backend
    And a ready note containing "The client sends SYN and waits."
    And a live card quoting "The client sends SYN and waits."
    When the user requests that note's cards
    Then that card's location points at the quoted passage

  @distill-flow @AC-13
  Scenario: A card whose quote survives only after normalization resolves at block precision
    Given a running notes backend
    And a ready note headed "TCP Handshake"
    And a live card quoting "TCP Handshake"
    When the user requests that note's cards
    Then that card's location covers the whole heading block

  @distill-flow @AC-13
  Scenario: A card whose quote no longer resolves reports no location and the note stays readable
    Given a running notes backend
    And a ready note containing "The client sends SYN and waits."
    And a live card quoting "a fragment that is no longer in this note"
    When the user requests that note
    And the user requests that note's cards
    Then the held note is still readable
    And that card reports no location
