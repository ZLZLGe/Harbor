(define (problem dock-to-shelf)
  (:domain warehouse-restock)
  (:objects
    bot1 - robot
    crate1 - crate
    receiving shelf-a - location
  )
  (:init
    (robot-at bot1 receiving)
    (crate-at crate1 receiving)
    (hands-free bot1)
    (connected receiving shelf-a)
    (connected shelf-a receiving)
  )
  (:goal
    (and
      (crate-at crate1 shelf-a)
    )
  )
)
