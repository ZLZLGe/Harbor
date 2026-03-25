(define (problem ridge-line)
  (:domain drone-survey)
  (:objects
    scout - drone
    camp ridge-a ridge-b - location
    target-a target-b - target
  )
  (:init
    (at scout camp)
    (base camp)
    (connected camp ridge-a)
    (connected ridge-a camp)
    (connected ridge-a ridge-b)
    (connected ridge-b ridge-a)
    (target-at target-a ridge-a)
    (target-at target-b ridge-b)
  )
  (:goal
    (and
      (uploaded target-a)
      (uploaded target-b)
    )
  )
)
