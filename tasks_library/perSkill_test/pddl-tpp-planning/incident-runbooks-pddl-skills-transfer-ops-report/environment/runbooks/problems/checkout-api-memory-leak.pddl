(define (problem checkout-api-memory-leak)
  (:domain incident-runbooks)
  (:objects
    checkout-api-memory-leak - incident
    checkout-api - service)
  (:init
    (alert-open checkout-api-memory-leak)
    (needs-restart checkout-api-memory-leak checkout-api))
  (:goal
    (resolved checkout-api-memory-leak)))
