(define (domain wetlab-assay)
  (:requirements :strips :typing)
  (:types sample reagent well plate incubator washer reader)

  (:predicates
    (on-plate ?well - well ?plate - plate)
    (sample-for ?sample - sample ?well - well)
    (reagent-for ?reagent - reagent ?well - well)
    (sample-available ?sample - sample)
    (reagent-available ?reagent - reagent)
    (aliquoted ?well - well)
    (reagent-added ?well - well)
    (mixed ?well - well)
    (ready-incubation ?plate - plate)
    (incubated ?plate - plate)
    (washed ?well - well)
    (ready-reader ?plate - plate)
    (reader-loaded ?plate - plate ?reader - reader)
    (readout ?well - well)
    (assay-complete ?plate - plate)
    (incubator-for ?plate - plate ?incubator - incubator)
    (washer-for ?plate - plate ?washer - washer)
    (reader-for ?plate - plate ?reader - reader)
    (current-mix ?well - well)
    (mix-next ?well - well ?next - well)
    (mix-terminal ?well - well)
    (current-wash ?well - well)
    (wash-next ?well - well ?next - well)
    (wash-terminal ?well - well)
    (current-read ?well - well)
    (read-next ?well - well ?next - well)
    (read-terminal ?well - well)
  )

  (:action aliquot-sample
    :parameters (?sample - sample ?well - well ?plate - plate)
    :precondition (and
      (sample-for ?sample ?well)
      (sample-available ?sample)
      (on-plate ?well ?plate)
    )
    :effect (and
      (aliquoted ?well)
      (not (sample-available ?sample))
    )
  )

  (:action add-reagent
    :parameters (?reagent - reagent ?well - well ?plate - plate)
    :precondition (and
      (reagent-for ?reagent ?well)
      (reagent-available ?reagent)
      (on-plate ?well ?plate)
      (aliquoted ?well)
    )
    :effect (and
      (reagent-added ?well)
      (not (reagent-available ?reagent))
    )
  )

  (:action mix-well
    :parameters (?well - well ?next - well ?plate - plate)
    :precondition (and
      (on-plate ?well ?plate)
      (current-mix ?well)
      (mix-next ?well ?next)
      (aliquoted ?well)
      (reagent-added ?well)
    )
    :effect (and
      (mixed ?well)
      (not (current-mix ?well))
      (current-mix ?next)
    )
  )

  (:action mix-final-well
    :parameters (?well - well ?plate - plate)
    :precondition (and
      (on-plate ?well ?plate)
      (current-mix ?well)
      (mix-terminal ?well)
      (aliquoted ?well)
      (reagent-added ?well)
    )
    :effect (and
      (mixed ?well)
      (not (current-mix ?well))
      (ready-incubation ?plate)
    )
  )

  (:action incubate-plate
    :parameters (?plate - plate ?incubator - incubator)
    :precondition (and
      (incubator-for ?plate ?incubator)
      (ready-incubation ?plate)
    )
    :effect (and
      (incubated ?plate)
      (not (ready-incubation ?plate))
    )
  )

  (:action wash-well
    :parameters (?well - well ?next - well ?plate - plate ?washer - washer)
    :precondition (and
      (washer-for ?plate ?washer)
      (on-plate ?well ?plate)
      (incubated ?plate)
      (mixed ?well)
      (current-wash ?well)
      (wash-next ?well ?next)
    )
    :effect (and
      (washed ?well)
      (not (current-wash ?well))
      (current-wash ?next)
    )
  )

  (:action wash-final-well
    :parameters (?well - well ?plate - plate ?washer - washer)
    :precondition (and
      (washer-for ?plate ?washer)
      (on-plate ?well ?plate)
      (incubated ?plate)
      (mixed ?well)
      (current-wash ?well)
      (wash-terminal ?well)
    )
    :effect (and
      (washed ?well)
      (not (current-wash ?well))
      (ready-reader ?plate)
    )
  )

  (:action load-reader
    :parameters (?plate - plate ?reader - reader)
    :precondition (and
      (reader-for ?plate ?reader)
      (incubated ?plate)
      (ready-reader ?plate)
    )
    :effect (and
      (reader-loaded ?plate ?reader)
      (not (ready-reader ?plate))
    )
  )

  (:action read-well
    :parameters (?well - well ?next - well ?plate - plate ?reader - reader)
    :precondition (and
      (reader-for ?plate ?reader)
      (reader-loaded ?plate ?reader)
      (on-plate ?well ?plate)
      (washed ?well)
      (current-read ?well)
      (read-next ?well ?next)
    )
    :effect (and
      (readout ?well)
      (not (current-read ?well))
      (current-read ?next)
    )
  )

  (:action read-final-well
    :parameters (?well - well ?plate - plate ?reader - reader)
    :precondition (and
      (reader-for ?plate ?reader)
      (reader-loaded ?plate ?reader)
      (on-plate ?well ?plate)
      (washed ?well)
      (current-read ?well)
      (read-terminal ?well)
    )
    :effect (and
      (readout ?well)
      (not (current-read ?well))
      (assay-complete ?plate)
    )
  )
)
