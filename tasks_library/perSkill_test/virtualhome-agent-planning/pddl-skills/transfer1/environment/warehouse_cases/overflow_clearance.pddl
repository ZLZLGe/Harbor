(define (problem overflow-clearance)
  (:domain warehouse-restock)
  (:objects
    bot1 - robot
    crate1 - crate
    qa staging outbound - location
  )
  (:init
    (robot-at bot1 qa)
    (crate-at crate1 staging)
    (hands-free bot1)
    (connected qa staging)
    (connected staging qa)
    (connected staging outbound)
    (connected outbound staging)
  )
  (:goal
    (and
      (crate-at crate1 outbound)
    )
  )
)
