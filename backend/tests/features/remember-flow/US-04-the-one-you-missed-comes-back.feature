Feature: The one you missed comes back before you stand up

  @remember-flow @AC-09
  Scenario: A card given the lowest grade is presented again before the sitting ends
    Given a remember review backend
    And the catalog has a due card "retry-me"
    And the user has started a review
    And the user has revealed the current card's back
    When the user grades the current card as "forgot"
    Then the same card is presented again before the sitting ends

  @remember-flow @AC-09
  Scenario: A card graded hard is presented again before the sitting ends
    Given a remember review backend
    And the catalog has a due card "hard-retry"
    And the user has started a review
    And the user has revealed the current card's back
    When the user grades the current card as "hard"
    Then the same card is presented again before the sitting ends

  @remember-flow @AC-09
  Scenario: A card shown the configured number of times counts as finished without a good grade
    Given a remember review backend
    And the catalog has a due card "show-limit"
    And the user has started a review
    And the user has revealed the current card's back
    When the user grades the current card as "forgot"
    And the user has revealed the current card's back
    And the user grades the current card as "forgot"
    Then the sitting ends without presenting that card again

  @remember-flow @AC-09
  Scenario: A card finished in the sitting stays out even when still due by schedule
    Given a remember review backend
    And the catalog has due cards "finished-by-grade" and "still-going"
    And the user has started a review
    And the card "finished-by-grade" is the one in front
    And the user has revealed the current card's back
    When the user grades the current card as "good"
    And the card "finished-by-grade" still has a next due date in the past
    Then the card "finished-by-grade" is not presented again before the sitting ends
