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

  @remember-flow @AC-01
  Scenario: A card discarded elsewhere drops out of the sitting when the live set is read
    Given a remember review backend
    And the catalog has due cards "keep-me" and "drop-me"
    And the user has started a review
    When the card "drop-me" is discarded from the catalog
    And the sitting's live membership is read
    Then the live set excludes the card "drop-me"
    And the sitting's stored set still contains the card "drop-me"

  @remember-flow @AC-01
  Scenario: A card with a stale scheduler stamp is treated as due
    Given a remember review backend
    And the catalog has a due card "stale-stamp" with a stale memoized scheduler stamp
    When the user starts a review
    Then the opened sitting contains the due card "stale-stamp"
