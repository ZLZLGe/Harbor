(define (problem analytics-disk-pressure)
  (:domain incident-runbooks)
  (:objects
    analytics-disk-pressure - incident
    analytics-node-3 - host)
  (:init
    (alert-open analytics-disk-pressure)
    (needs-cleanup analytics-disk-pressure analytics-node-3)
    (cleanup-window analytics-node-3))
  (:goal
    (resolved analytics-disk-pressure)))
