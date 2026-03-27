(define (domain warehouse-restock)
  (:requirements :strips :typing)
  (:types robot crate location)
  (:predicates
    (robot-at ?r - robot ?l - location)
    (crate-at ?c - crate ?l - location)
    (connected ?from - location ?to - location)
    (carrying ?r - robot ?c - crate)
    (hands-free ?r - robot)
  )

  (:action move
    :parameters (?r - robot ?from - location ?to - location)
    :precondition (and (robot-at ?r ?from) (connected ?from ?to))
    :effect (and
      (not (robot-at ?r ?from))
      (robot-at ?r ?to)
    )
  )

  (:action pick
    :parameters (?r - robot ?c - crate ?l - location)
    :precondition (and (robot-at ?r ?l) (crate-at ?c ?l) (hands-free ?r))
    :effect (and
      (carrying ?r ?c)
      (not (crate-at ?c ?l))
      (not (hands-free ?r))
    )
  )

  (:action drop
    :parameters (?r - robot ?c - crate ?l - location)
    :precondition (and (robot-at ?r ?l) (carrying ?r ?c))
    :effect (and
      (crate-at ?c ?l)
      (hands-free ?r)
      (not (carrying ?r ?c))
    )
  )
)
