(define (problem registry-backup-gap)
  (:domain incident-runbooks)
  (:objects
    registry-backup-gap - incident
    registry-service - service
    snapshot-20260318 - backup)
  (:init
    (alert-open registry-backup-gap)
    (needs-restore registry-backup-gap registry-service snapshot-20260318))
  (:goal
    (resolved registry-backup-gap)))
