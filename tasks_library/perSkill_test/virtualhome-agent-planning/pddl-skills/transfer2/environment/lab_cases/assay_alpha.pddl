(define (problem assay-alpha)
  (:domain lab-assay)
  (:objects
    sample-a - sample
  )
  (:init
    (raw sample-a)
    (buffer-ready)
    (centrifuge-ready)
    (analyzer-ready)
  )
  (:goal
    (and
      (archived sample-a)
    )
  )
)
