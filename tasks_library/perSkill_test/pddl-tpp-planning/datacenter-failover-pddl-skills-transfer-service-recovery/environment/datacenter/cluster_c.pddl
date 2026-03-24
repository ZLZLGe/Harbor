(define (problem cluster-c-recovery)
  (:domain datacenter-failover)

  (:objects
    cluster-c - cluster
    profile-db session-edge - service
    dc-primary dc-backup - site
    gateway-c - gateway
    replica-c1 replica-c2 - replica
  )

  (:init
    (standby-site cluster-c dc-backup)
    (failed-site cluster-c dc-primary)
    (uses-gateway cluster-c gateway-c)
    (core-role cluster-c profile-db)
    (edge-role cluster-c session-edge)
    (can-host profile-db dc-backup)
    (can-host session-edge dc-backup)
    (secondary-synced cluster-c dc-backup)
    (rebuild-target cluster-c replica-c1 dc-primary)
    (rebuild-target cluster-c replica-c2 dc-primary)
  )

  (:goal
    (and
      (core-online cluster-c profile-db dc-backup)
      (edge-online cluster-c session-edge dc-backup)
      (traffic-cutover cluster-c gateway-c dc-backup)
      (rebuilt cluster-c replica-c1 dc-primary)
      (rebuilt cluster-c replica-c2 dc-primary)
    )
  )
)
