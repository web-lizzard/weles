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

  @remember-flow @AC-04
  Scenario: The same card stays in front across separate requests for one sitting
    Given a remember review backend
    And the catalog has a due card "stable-front"
    And the user has started a review
    When the user reads the current card
    And the user reads the current card again
    Then both readings show the same card

  @remember-flow @AC-04
  Scenario: The card just graded is not the next card shown
    Given a remember review backend
    And the catalog has due cards "first", "second", and "third"
    And the user has started a review
    And the user has revealed the current card's back
    When the user grades the current card as "forgot"
    Then the next card shown is not the card just graded

  @remember-flow @AC-05
  Scenario: Grades given before leaving a sitting still count afterward
    Given a remember review backend
    And the catalog has a due card "graded-then-left"
    And the user has started a review
    And the user has revealed the current card's back
    And the user grades the current card as "good"
    When the user starts a review again
    Then the grade from the prior sitting is recorded for the card "graded-then-left"

  @remember-flow @AC-05
  Scenario: Cards not reached in an abandoned sitting are still due next time
    Given a remember review backend
    And the catalog has due cards "done-one" and "skipped-one"
    And the user has started a review
    And the card "done-one" is the one in front
    And the user has revealed the current card's back
    And the user grades the current card as "good"
    When the user starts a review again
    Then the opened sitting contains the due card "skipped-one"
