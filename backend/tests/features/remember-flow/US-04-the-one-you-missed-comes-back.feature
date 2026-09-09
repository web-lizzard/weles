Feature: The one you missed comes back before you stand up

  @remember-flow @AC-09
  Scenario: A card given the lowest grade is presented again before the sitting ends
    Given a remember review backend
    And the catalog has a due card "retry-me"
    And the user has started a review
    And the user has revealed the current card's back
    When the user grades the current card as "forgot"
    Then the same card is presented again before the sitting ends
