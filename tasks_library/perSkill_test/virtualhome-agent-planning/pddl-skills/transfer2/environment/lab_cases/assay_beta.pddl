(define (problem assay-beta)
  (:domain lab-assay)
  (:objects
    sample-b1 sample-b2 - sample
  )
  (:init
    (raw sample-b1)
    (raw sample-b2)
    (buffer-ready)
    (centrifuge-ready)
    (analyzer-ready)
  )
  (:goal
    (and
      (archived sample-b1)
      (archived sample-b2)
    )
  )
)
