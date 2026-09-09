Feature: Everything due, in one command

  @remember-flow @AC-01
  Scenario: Starting a review opens a session with every due card
    Given a remember review backend
    And the catalog has a due card "alpha" and a not-due card "beta"
    When the user starts a review
    Then the opened sitting contains every due card
    And the opened sitting excludes cards that are not due

  @remember-flow @AC-02
  Scenario: Starting a review when nothing is due reports it and creates no session
    Given a remember review backend
    And the catalog has no due cards
    When the user starts a review
    Then the user is told nothing is due
    And no sitting was created
