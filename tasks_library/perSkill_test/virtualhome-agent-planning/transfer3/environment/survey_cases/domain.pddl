(define (domain drone-survey)
  (:requirements :strips :typing)
  (:types drone location target)
  (:predicates
    (at ?d - drone ?l - location)
    (connected ?from - location ?to - location)
    (target-at ?t - target ?l - location)
    (camera-calibrated ?d - drone)
    (captured ?t - target)
    (uploaded ?t - target)
    (base ?l - location)
  )

  (:action fly
    :parameters (?d - drone ?from - location ?to - location)
    :precondition (and (at ?d ?from) (connected ?from ?to))
    :effect (and
      (not (at ?d ?from))
      (at ?d ?to)
      (not (camera-calibrated ?d))
    )
  )

  (:action calibrate-camera
    :parameters (?d - drone ?l - location)
    :precondition (at ?d ?l)
    :effect (camera-calibrated ?d)
  )

  (:action capture-photo
    :parameters (?d - drone ?t - target ?l - location)
    :precondition (and (at ?d ?l) (target-at ?t ?l) (camera-calibrated ?d))
    :effect (captured ?t)
  )

  (:action upload-photo
    :parameters (?d - drone ?t - target ?l - location)
    :precondition (and (at ?d ?l) (base ?l) (captured ?t))
    :effect (uploaded ?t)
  )
)
