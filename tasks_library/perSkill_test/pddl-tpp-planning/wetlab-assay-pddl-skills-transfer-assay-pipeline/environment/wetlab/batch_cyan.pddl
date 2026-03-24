(define (problem batch-cyan)
  (:domain wetlab-assay)

  (:objects
    plate-cyan - plate
    inc-25b - incubator
    wash-sigma - washer
    reader-sigma - reader
    well-c1 well-c2 well-c3 well-c4 - well
    plasma-c1 plasma-c2 plasma-c3 plasma-c4 - sample
    enzyme-c1 enzyme-c2 enzyme-c3 enzyme-c4 - reagent
  )

  (:init
    (incubator-for plate-cyan inc-25b)
    (washer-for plate-cyan wash-sigma)
    (reader-for plate-cyan reader-sigma)

    (on-plate well-c1 plate-cyan)
    (on-plate well-c2 plate-cyan)
    (on-plate well-c3 plate-cyan)
    (on-plate well-c4 plate-cyan)

    (sample-for plasma-c1 well-c1)
    (sample-for plasma-c2 well-c2)
    (sample-for plasma-c3 well-c3)
    (sample-for plasma-c4 well-c4)

    (reagent-for enzyme-c1 well-c1)
    (reagent-for enzyme-c2 well-c2)
    (reagent-for enzyme-c3 well-c3)
    (reagent-for enzyme-c4 well-c4)

    (sample-available plasma-c1)
    (sample-available plasma-c2)
    (sample-available plasma-c3)
    (sample-available plasma-c4)

    (reagent-available enzyme-c1)
    (reagent-available enzyme-c2)
    (reagent-available enzyme-c3)
    (reagent-available enzyme-c4)

    (current-mix well-c1)
    (mix-next well-c1 well-c2)
    (mix-next well-c2 well-c3)
    (mix-next well-c3 well-c4)
    (mix-terminal well-c4)

    (current-wash well-c1)
    (wash-next well-c1 well-c2)
    (wash-next well-c2 well-c3)
    (wash-next well-c3 well-c4)
    (wash-terminal well-c4)

    (current-read well-c1)
    (read-next well-c1 well-c2)
    (read-next well-c2 well-c3)
    (read-next well-c3 well-c4)
    (read-terminal well-c4)
  )

  (:goal
    (and
      (assay-complete plate-cyan)
      (readout well-c1)
      (readout well-c2)
      (readout well-c3)
      (readout well-c4)
    )
  )
)
