(define (problem cluster-b-recovery)
  (:domain datacenter-failover)

  (:objects
    cluster-b - cluster
    ledger-store checkout-edge - service
    dc-north dc-south - site
    gateway-b - gateway
    replica-b1 replica-b2 - replica
  )

  (:init
    (standby-site cluster-b dc-south)
    (failed-site cluster-b dc-north)
    (uses-gateway cluster-b gateway-b)
    (core-role cluster-b ledger-store)
    (edge-role cluster-b checkout-edge)
    (can-host ledger-store dc-south)
    (can-host checkout-edge dc-south)
    (secondary-synced cluster-b dc-south)
    (rebuild-target cluster-b replica-b1 dc-north)
    (rebuild-target cluster-b replica-b2 dc-north)
  )

  (:goal
    (and
      (core-online cluster-b ledger-store dc-south)
      (edge-online cluster-b checkout-edge dc-south)
      (traffic-cutover cluster-b gateway-b dc-south)
      (rebuilt cluster-b replica-b1 dc-north)
      (rebuilt cluster-b replica-b2 dc-north)
    )
  )
)
