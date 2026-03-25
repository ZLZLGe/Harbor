(define (domain incident-runbooks)
  (:requirements :strips :typing)
  (:types incident service secret host cluster backup)
  (:predicates
    (alert-open ?i - incident)
    (acknowledged ?i - incident)
    (diagnosed ?i - incident)
    (needs-restart ?i - incident ?s - service)
    (restart-ready ?s - service)
    (service-restarted ?s - service)
    (needs-secret-rotation ?i - incident ?x - secret)
    (secret-access ?x - secret)
    (secret-rotated ?x - secret)
    (needs-cleanup ?i - incident ?h - host)
    (cleanup-window ?h - host)
    (host-cleaned ?h - host)
    (needs-failover ?i - incident ?c - cluster)
    (replica-healthy ?c - cluster)
    (cluster-failed-over ?c - cluster)
    (needs-restore ?i - incident ?s - service ?b - backup)
    (backup-available ?b - backup)
    (service-restored ?s - service)
    (resolved ?i - incident))

  (:action acknowledge
    :parameters (?i - incident)
    :precondition (alert-open ?i)
    :effect (and
      (acknowledged ?i)
      (not (alert-open ?i))))

  (:action inspect
    :parameters (?i - incident)
    :precondition (acknowledged ?i)
    :effect (diagnosed ?i))

  (:action drain-traffic
    :parameters (?i - incident ?s - service)
    :precondition (and
      (diagnosed ?i)
      (needs-restart ?i ?s))
    :effect (restart-ready ?s))

  (:action restart-service
    :parameters (?i - incident ?s - service)
    :precondition (and
      (diagnosed ?i)
      (needs-restart ?i ?s)
      (restart-ready ?s))
    :effect (service-restarted ?s))

  (:action rotate-secret
    :parameters (?i - incident ?x - secret)
    :precondition (and
      (diagnosed ?i)
      (needs-secret-rotation ?i ?x)
      (secret-access ?x))
    :effect (secret-rotated ?x))

  (:action prune-logs
    :parameters (?i - incident ?h - host)
    :precondition (and
      (diagnosed ?i)
      (needs-cleanup ?i ?h)
      (cleanup-window ?h))
    :effect (host-cleaned ?h))

  (:action promote-replica
    :parameters (?i - incident ?c - cluster)
    :precondition (and
      (diagnosed ?i)
      (needs-failover ?i ?c)
      (replica-healthy ?c))
    :effect (cluster-failed-over ?c))

  (:action restore-backup
    :parameters (?i - incident ?s - service ?b - backup)
    :precondition (and
      (diagnosed ?i)
      (needs-restore ?i ?s ?b)
      (backup-available ?b))
    :effect (service-restored ?s))

  (:action close-after-restart
    :parameters (?i - incident ?s - service)
    :precondition (and
      (diagnosed ?i)
      (needs-restart ?i ?s)
      (service-restarted ?s))
    :effect (resolved ?i))

  (:action close-after-rotation
    :parameters (?i - incident ?x - secret)
    :precondition (and
      (diagnosed ?i)
      (needs-secret-rotation ?i ?x)
      (secret-rotated ?x))
    :effect (resolved ?i))

  (:action close-after-cleanup
    :parameters (?i - incident ?h - host)
    :precondition (and
      (diagnosed ?i)
      (needs-cleanup ?i ?h)
      (host-cleaned ?h))
    :effect (resolved ?i))

  (:action close-after-failover
    :parameters (?i - incident ?c - cluster)
    :precondition (and
      (diagnosed ?i)
      (needs-failover ?i ?c)
      (cluster-failed-over ?c))
    :effect (resolved ?i))

  (:action close-after-restore
    :parameters (?i - incident ?s - service ?b - backup)
    :precondition (and
      (diagnosed ?i)
      (needs-restore ?i ?s ?b)
      (service-restored ?s))
    :effect (resolved ?i)))
