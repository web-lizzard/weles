Feature: Never pick a date

  @remember-flow @AC-06
  Scenario: Grading a card sets when it next comes up without the user naming a date
    Given a remember review backend
    And the catalog has a due card "schedule-me"
    And the user has started a review
    And the user has revealed the current card's back
    When the user grades the current card as "good"
    Then the card has a scheduled next due date

  @remember-flow @AC-07
  Scenario: A card graded well repeatedly returns after progressively longer gaps
    Given a remember review backend
    And the catalog has a due card "interval-me"
    And the card has two prior good grades in its history
    When the user starts a review
    And the user has revealed the current card's back
    And the user grades the current card as "good"
    Then the next due date is farther out than after the second good grade

  @remember-flow @AC-08
  Scenario: Grading a card leaves its front and back unchanged
    Given a remember review backend
    And the catalog has a due card "stable-me" with front "Front text" and back "Back text"
    And the user has started a review
    And the user has revealed the current card's back
    When the user grades the current card as "hard"
    Then the card still shows front "Front text" and back "Back text"
