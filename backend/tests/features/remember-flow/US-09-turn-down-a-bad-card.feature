Feature: Turn down a bad card where you meet it

  @remember-flow @AC-17
  Scenario: A rejected card is not offered in a later review
    Given a remember review backend
    And the catalog has due cards "bad-card" and "keep-me"
    And the user has started a review
    And the card "bad-card" is the one in front
    And the user has revealed the current card's back
    When the user rejects the current card
    And the remember worker drains the outbox once
    And the user reads the current card
    And the user has revealed the current card's back
    And the user grades the current card as "good"
    And the card "keep-me" still has a next due date in the past
    And the user starts a review again
    Then the opened sitting excludes the card "bad-card"
    And the opened sitting contains the due card "keep-me"

  @remember-flow @AC-23
  Scenario: A user rejection is recorded as the user's own judgement
    Given a remember review backend
    And the catalog has a due card "user-rejected"
    And a card "system-rejected" was discarded by the system as ungrounded
    And the user has started a review
    And the user has revealed the current card's back
    When the user rejects the current card
    And the remember worker drains the outbox once
    Then the card "user-rejected" has a discard whose reason is "user_audit"
    And the card "system-rejected" has a discard whose reason is "ungrounded"
