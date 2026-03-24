(define (problem night-window-alpha)
  (:domain observatory-night)
  (:objects
    scope1 - telescope
    park att-auriga att-cygnus relay - attitude
    auriga cygnus - target
    s0 s1 s2 s3 s4 s5 s6 s7 s8 s9 s10 - slot)

  (:init
    (current-attitude scope1 park)
    (stable scope1)
    (buffer-free scope1)
    (slew-link park att-auriga)
    (slew-link att-auriga relay)
    (slew-link relay att-cygnus)
    (slew-link att-cygnus relay)
    (points-at att-auriga auriga)
    (points-at att-cygnus cygnus)
    (relay-attitude relay)
    (requested auriga)
    (requested cygnus)
    (target-visible auriga s2)
    (target-visible cygnus s7)
    (link-visible s4)
    (link-visible s9)
    (current-slot s0)
    (next-slot s1 s0)
    (next-slot s2 s1)
    (next-slot s3 s2)
    (next-slot s4 s3)
    (next-slot s5 s4)
    (next-slot s6 s5)
    (next-slot s7 s6)
    (next-slot s8 s7)
    (next-slot s9 s8)
    (next-slot s10 s9))

  (:goal (and
    (sent auriga)
    (sent cygnus)))
)
