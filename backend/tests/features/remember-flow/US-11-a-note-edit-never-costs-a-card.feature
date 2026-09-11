Feature: A note edit never costs a card

  @remember-flow @AC-19
  Scenario: A card whose fragment no longer resolves is still presented and graded
    Given a remember review backend
    And the catalog has a due card "still-mine" with its note rewritten after minting
    And the user has started a review
    And the user has revealed the current card's back
    When the user grades the current card as "good"
    Then the grade is recorded for that card

  @remember-flow @AC-20
  Scenario: A card whose fragment no longer resolves offers no source route and no message
    Given a remember review backend
    And the catalog has a due card "orphan-quote" with its note rewritten after minting
    And the user has started a review
    And the user has revealed the current card's back
    When the user tries to read the current card's source
    Then the source is not available
    And no source-unavailability message is offered
