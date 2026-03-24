(define (problem batch-gold)
  (:domain wetlab-assay)

  (:objects
    plate-gold - plate
    inc-42z - incubator
    wash-tau - washer
    reader-tau - reader
    well-g1 well-g2 well-g3 well-g4 well-g5 - well
    serum-g1 serum-g2 serum-g3 serum-g4 serum-g5 - sample
    substrate-g1 substrate-g2 substrate-g3 substrate-g4 substrate-g5 - reagent
  )

  (:init
    (incubator-for plate-gold inc-42z)
    (washer-for plate-gold wash-tau)
    (reader-for plate-gold reader-tau)

    (on-plate well-g1 plate-gold)
    (on-plate well-g2 plate-gold)
    (on-plate well-g3 plate-gold)
    (on-plate well-g4 plate-gold)
    (on-plate well-g5 plate-gold)

    (sample-for serum-g1 well-g1)
    (sample-for serum-g2 well-g2)
    (sample-for serum-g3 well-g3)
    (sample-for serum-g4 well-g4)
    (sample-for serum-g5 well-g5)

    (reagent-for substrate-g1 well-g1)
    (reagent-for substrate-g2 well-g2)
    (reagent-for substrate-g3 well-g3)
    (reagent-for substrate-g4 well-g4)
    (reagent-for substrate-g5 well-g5)

    (sample-available serum-g1)
    (sample-available serum-g2)
    (sample-available serum-g3)
    (sample-available serum-g4)
    (sample-available serum-g5)

    (reagent-available substrate-g1)
    (reagent-available substrate-g2)
    (reagent-available substrate-g3)
    (reagent-available substrate-g4)
    (reagent-available substrate-g5)

    (current-mix well-g1)
    (mix-next well-g1 well-g2)
    (mix-next well-g2 well-g3)
    (mix-next well-g3 well-g4)
    (mix-next well-g4 well-g5)
    (mix-terminal well-g5)

    (current-wash well-g1)
    (wash-next well-g1 well-g2)
    (wash-next well-g2 well-g3)
    (wash-next well-g3 well-g4)
    (wash-next well-g4 well-g5)
    (wash-terminal well-g5)

    (current-read well-g1)
    (read-next well-g1 well-g2)
    (read-next well-g2 well-g3)
    (read-next well-g3 well-g4)
    (read-next well-g4 well-g5)
    (read-terminal well-g5)
  )

  (:goal
    (and
      (assay-complete plate-gold)
      (readout well-g1)
      (readout well-g2)
      (readout well-g3)
      (readout well-g4)
      (readout well-g5)
    )
  )
)
