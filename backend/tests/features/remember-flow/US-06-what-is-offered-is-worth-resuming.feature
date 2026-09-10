Feature: What is offered to resume is still worth resuming

  @remember-flow @AC-12
  Scenario: A sitting past its horizon is not offered for resumption
    Given a remember review backend
    And the resume horizon is 1 hours
    And the catalog has due cards "alpha" and "beta"
    And the user has started a review
    When the clock advances by 2 hours
    And the user starts a review again
    Then the sitting is newly opened
    And the opened sitting is not the same sitting as before

  @remember-flow @AC-13
  Scenario: Grades from an expired sitting keep counting toward the schedule
    Given a remember review backend
    And the resume horizon is 1 hours
    And the catalog has due cards "graded" and "left-behind"
    And the user has started a review
    And the card "graded" is the one in front
    When the user has revealed the current card's back
    And the user grades the current card as "good"
    And the clock advances by 2 hours
    And the user starts a review again
    Then the sitting is newly opened
    And the grade from the prior sitting is recorded for the card "graded"
    And the opened sitting contains the due card "left-behind"
    And the opened sitting excludes the card "graded"

  @remember-flow @AC-13
  Scenario: An ungraded card from an expired sitting appears in the fresh sitting
    Given a remember review backend
    And the resume horizon is 1 hours
    And the catalog has due cards "still-due" and "other-due"
    And the user has started a review
    And the card "still-due" is the one in front
    When the clock advances by 2 hours
    And the user starts a review again
    Then the sitting is newly opened
    And the opened sitting contains the due card "still-due"
