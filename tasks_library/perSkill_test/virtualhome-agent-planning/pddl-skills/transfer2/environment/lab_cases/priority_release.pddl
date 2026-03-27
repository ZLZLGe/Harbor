(define (problem priority-release)
  (:domain lab-assay)
  (:objects
    sample-c1 sample-c2 - sample
  )
  (:init
    (raw sample-c1)
    (thawed sample-c2)
    (buffer-ready)
    (centrifuge-ready)
    (analyzer-ready)
  )
  (:goal
    (and
      (archived sample-c1)
      (archived sample-c2)
    )
  )
)
