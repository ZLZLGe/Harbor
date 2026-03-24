(define (problem cluster-a-recovery)
  (:domain datacenter-failover)

  (:objects
    cluster-a - cluster
    auth-store api-frontdoor - service
    dc-east dc-west - site
    gateway-a - gateway
    replica-a1 replica-a2 - replica
  )

  (:init
    (standby-site cluster-a dc-west)
    (failed-site cluster-a dc-east)
    (uses-gateway cluster-a gateway-a)
    (core-role cluster-a auth-store)
    (edge-role cluster-a api-frontdoor)
    (can-host auth-store dc-west)
    (can-host api-frontdoor dc-west)
    (secondary-synced cluster-a dc-west)
    (rebuild-target cluster-a replica-a1 dc-east)
    (rebuild-target cluster-a replica-a2 dc-east)
  )

  (:goal
    (and
      (core-online cluster-a auth-store dc-west)
      (edge-online cluster-a api-frontdoor dc-west)
      (traffic-cutover cluster-a gateway-a dc-west)
      (rebuilt cluster-a replica-a1 dc-east)
      (rebuilt cluster-a replica-a2 dc-east)
    )
  )
)
