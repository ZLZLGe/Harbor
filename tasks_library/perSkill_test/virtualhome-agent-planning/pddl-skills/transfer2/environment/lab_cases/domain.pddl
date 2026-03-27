(define (domain lab-assay)
  (:requirements :strips :typing)
  (:types sample)
  (:predicates
    (raw ?s - sample)
    (thawed ?s - sample)
    (buffered ?s - sample)
    (spun ?s - sample)
    (analyzed ?s - sample)
    (archived ?s - sample)
    (buffer-ready)
    (centrifuge-ready)
    (analyzer-ready)
  )

  (:action thaw-sample
    :parameters (?s - sample)
    :precondition (raw ?s)
    :effect (and
      (thawed ?s)
      (not (raw ?s))
    )
  )

  (:action add-buffer
    :parameters (?s - sample)
    :precondition (and (thawed ?s) (buffer-ready))
    :effect (and
      (buffered ?s)
      (not (thawed ?s))
    )
  )

  (:action spin-sample
    :parameters (?s - sample)
    :precondition (and (buffered ?s) (centrifuge-ready))
    :effect (and
      (spun ?s)
      (not (buffered ?s))
    )
  )

  (:action analyze-sample
    :parameters (?s - sample)
    :precondition (and (spun ?s) (analyzer-ready))
    :effect (and
      (analyzed ?s)
      (not (spun ?s))
    )
  )

  (:action archive-sample
    :parameters (?s - sample)
    :precondition (analyzed ?s)
    :effect (and
      (archived ?s)
      (not (analyzed ?s))
    )
  )
)
