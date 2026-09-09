Feature: Answer before you are shown it

  @remember-flow @AC-03
  Scenario: A card's back stays hidden until the user reveals it
    Given a remember review backend
    And the catalog has a due card "recall-me"
    And the user has started a review
    Then the current card shows only the front
    When the user reveals the current card's back
    Then the current card shows the back

  @remember-flow @AC-04
  Scenario: Exactly one card is in front of the user at a time
    Given a remember review backend
    And the catalog has due cards "one", "two", and "three"
    And the user has started a review
    Then exactly one card is in front of the user

  @remember-flow @AC-05
  Scenario: After revealing the back the user records recall as one of four steps
    Given a remember review backend
    And the catalog has a due card "grade-me"
    And the user has started a review
    And the user has revealed the current card's back
    When the user grades the current card as "good"
    Then the grade is recorded for that card
