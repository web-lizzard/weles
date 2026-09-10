Feature: See what is waiting without sitting down

  @remember-flow @AC-14
  Scenario: Reading the due count does not start a review session
    Given a remember review backend
    And the catalog has a due card "waiting"
    When the user reads the due count
    Then the due total is 1
    And no sitting was created

  @remember-flow @AC-15
  Scenario: The due total rises when a card becomes due without starting a review
    Given a remember review backend
    And the catalog has a card "ripening" that is not yet due
    When the user reads the due count
    Then the due total is 0
    When the clock advances enough for the card "ripening" to become due
    And the user reads the due count
    Then the due total is 1
