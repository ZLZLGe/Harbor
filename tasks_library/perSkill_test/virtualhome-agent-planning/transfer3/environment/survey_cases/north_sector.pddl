(define (problem north-sector)
  (:domain drone-survey)
  (:objects
    scout - drone
    hangar ridge - location
    target-a - target
  )
  (:init
    (at scout hangar)
    (base hangar)
    (connected hangar ridge)
    (connected ridge hangar)
    (target-at target-a ridge)
  )
  (:goal
    (and
      (uploaded target-a)
    )
  )
)
