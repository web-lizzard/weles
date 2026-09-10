Feature: Walking away costs nothing

  @remember-flow @AC-10
  Scenario: A grade given before leaving still counts on the schedule after returning
    Given a remember review backend
    And the catalog has due cards "alpha" and "beta"
    And the user has started a review
    And the card "alpha" is the one in front
    When the user has revealed the current card's back
    And the user grades the current card as "good"
    And the user starts a review again
    Then the grade from the prior sitting is recorded for the card "alpha"
    And the card "alpha" has a scheduled next due date

  @remember-flow @AC-11
  Scenario: Returning continues the same sitting with only outstanding cards
    Given a remember review backend
    And the catalog has due cards "alpha" and "beta"
    And the user has started a review
    And the card "alpha" is the one in front
    When the user has revealed the current card's back
    And the user grades the current card as "good"
    And the user starts a review again
    Then the sitting is resumed
    And the resumed sitting is the same sitting as before
    And the outstanding count is 1
    And the card "alpha" is not the one in front

  @remember-flow @AC-11
  Scenario: Re-opening does not create a second sitting
    Given a remember review backend
    And the catalog has due cards "alpha" and "beta"
    And the user has started a review
    When the user starts a review again
    Then the sitting is resumed
    And only one sitting exists
