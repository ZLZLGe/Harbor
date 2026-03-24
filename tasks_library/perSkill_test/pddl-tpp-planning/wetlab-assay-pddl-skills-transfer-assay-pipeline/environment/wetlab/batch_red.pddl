(define (problem batch-red)
  (:domain wetlab-assay)

  (:objects
    plate-red - plate
    inc-37a - incubator
    wash-rho - washer
    reader-rho - reader
    well-r1 well-r2 well-r3 - well
    lysate-r1 lysate-r2 lysate-r3 - sample
    chromogen-r1 chromogen-r2 chromogen-r3 - reagent
  )

  (:init
    (incubator-for plate-red inc-37a)
    (washer-for plate-red wash-rho)
    (reader-for plate-red reader-rho)

    (on-plate well-r1 plate-red)
    (on-plate well-r2 plate-red)
    (on-plate well-r3 plate-red)

    (sample-for lysate-r1 well-r1)
    (sample-for lysate-r2 well-r2)
    (sample-for lysate-r3 well-r3)

    (reagent-for chromogen-r1 well-r1)
    (reagent-for chromogen-r2 well-r2)
    (reagent-for chromogen-r3 well-r3)

    (sample-available lysate-r1)
    (sample-available lysate-r2)
    (sample-available lysate-r3)

    (reagent-available chromogen-r1)
    (reagent-available chromogen-r2)
    (reagent-available chromogen-r3)

    (current-mix well-r1)
    (mix-next well-r1 well-r2)
    (mix-next well-r2 well-r3)
    (mix-terminal well-r3)

    (current-wash well-r1)
    (wash-next well-r1 well-r2)
    (wash-next well-r2 well-r3)
    (wash-terminal well-r3)

    (current-read well-r1)
    (read-next well-r1 well-r2)
    (read-next well-r2 well-r3)
    (read-terminal well-r3)
  )

  (:goal
    (and
      (assay-complete plate-red)
      (readout well-r1)
      (readout well-r2)
      (readout well-r3)
    )
  )
)
