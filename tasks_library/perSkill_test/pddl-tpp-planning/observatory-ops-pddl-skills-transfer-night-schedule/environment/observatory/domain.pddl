(define (domain observatory-night)
  (:requirements :strips :typing)
  (:types telescope attitude target slot)

  (:predicates
    (current-attitude ?o - telescope ?a - attitude)
    (slew-link ?from ?to - attitude)
    (stable ?o - telescope)
    (buffer-free ?o - telescope)
    (points-at ?a - attitude ?t - target)
    (relay-attitude ?a - attitude)
    (requested ?t - target)
    (captured ?t - target)
    (sent ?t - target)
    (target-visible ?t - target ?s - slot)
    (link-visible ?s - slot)
    (current-slot ?s - slot)
    (next-slot ?next ?curr - slot))

  (:action slew
    :parameters (?o - telescope ?from ?to - attitude ?curr ?next - slot)
    :precondition (and
      (current-attitude ?o ?from)
      (slew-link ?from ?to)
      (current-slot ?curr)
      (next-slot ?next ?curr))
    :effect (and
      (not (current-attitude ?o ?from))
      (current-attitude ?o ?to)
      (not (current-slot ?curr))
      (current-slot ?next)
      (not (stable ?o))))

  (:action calibrate
    :parameters (?o - telescope ?a - attitude ?curr ?next - slot)
    :precondition (and
      (current-attitude ?o ?a)
      (current-slot ?curr)
      (next-slot ?next ?curr))
    :effect (and
      (not (current-slot ?curr))
      (current-slot ?next)
      (stable ?o)))

  (:action observe
    :parameters (?o - telescope ?t - target ?a - attitude ?curr ?next - slot)
    :precondition (and
      (current-attitude ?o ?a)
      (points-at ?a ?t)
      (requested ?t)
      (stable ?o)
      (buffer-free ?o)
      (target-visible ?t ?curr)
      (current-slot ?curr)
      (next-slot ?next ?curr))
    :effect (and
      (captured ?t)
      (not (buffer-free ?o))
      (not (current-slot ?curr))
      (current-slot ?next)))

  (:action downlink
    :parameters (?o - telescope ?t - target ?a - attitude ?curr ?next - slot)
    :precondition (and
      (current-attitude ?o ?a)
      (relay-attitude ?a)
      (captured ?t)
      (link-visible ?curr)
      (current-slot ?curr)
      (next-slot ?next ?curr))
    :effect (and
      (sent ?t)
      (not (requested ?t))
      (not (captured ?t))
      (buffer-free ?o)
      (not (current-slot ?curr))
      (current-slot ?next))))
