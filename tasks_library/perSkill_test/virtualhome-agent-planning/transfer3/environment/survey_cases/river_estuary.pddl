(define (problem river-estuary)
  (:domain drone-survey)
  (:objects
    scout - drone
    dock estuary delta - location
    target-a target-b - target
  )
  (:init
    (at scout dock)
    (base dock)
    (connected dock estuary)
    (connected estuary dock)
    (connected estuary delta)
    (connected delta estuary)
    (target-at target-a estuary)
    (target-at target-b delta)
  )
  (:goal
    (and
      (uploaded target-a)
      (uploaded target-b)
    )
  )
)
