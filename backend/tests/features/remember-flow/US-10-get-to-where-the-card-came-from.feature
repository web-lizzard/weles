Feature: Get to where the card came from

  @remember-flow @AC-18
  Scenario: The source is unavailable before the back is revealed
    Given a remember review backend
    And the catalog has a due card "jump-me" with a resolvable source fragment
    And the user has started a review
    When the user tries to read the current card's source
    Then the source is not available

  @remember-flow @AC-18
  Scenario: After the back is revealed the user reaches the marked fragment
    Given a remember review backend
    And the catalog has a due card "jump-me" with a resolvable source fragment
    And the user has started a review
    And the user has revealed the current card's back
    When the user reads the current card's source
    Then the source shows the fragment marked in the note
