(define (problem inspection-rebalance)
  (:domain warehouse-restock)
  (:objects
    bot1 - robot
    crate1 crate2 - crate
    receiving hub shelf-b shelf-c - location
  )
  (:init
    (robot-at bot1 receiving)
    (crate-at crate1 receiving)
    (crate-at crate2 hub)
    (hands-free bot1)
    (connected receiving hub)
    (connected hub receiving)
    (connected hub shelf-b)
    (connected shelf-b hub)
    (connected hub shelf-c)
    (connected shelf-c hub)
  )
  (:goal
    (and
      (crate-at crate1 shelf-b)
      (crate-at crate2 shelf-c)
    )
  )
)
