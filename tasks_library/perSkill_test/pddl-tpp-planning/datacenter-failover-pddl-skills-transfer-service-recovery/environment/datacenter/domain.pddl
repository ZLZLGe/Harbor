(define (domain datacenter-failover)
  (:requirements :strips :typing)
  (:types cluster service site gateway replica)

  (:predicates
    (standby-site ?cluster - cluster ?site - site)
    (failed-site ?cluster - cluster ?site - site)
    (uses-gateway ?cluster - cluster ?gateway - gateway)
    (core-role ?cluster - cluster ?service - service)
    (edge-role ?cluster - cluster ?service - service)
    (can-host ?service - service ?site - site)
    (secondary-synced ?cluster - cluster ?site - site)
    (rebuild-target ?cluster - cluster ?replica - replica ?site - site)
    (link-restored ?cluster - cluster)
    (primary-promoted ?cluster - cluster ?site - site)
    (core-online ?cluster - cluster ?service - service ?site - site)
    (edge-online ?cluster - cluster ?service - service ?site - site)
    (stabilized ?cluster - cluster)
    (traffic-cutover ?cluster - cluster ?gateway - gateway ?site - site)
    (rebuilt ?cluster - cluster ?replica - replica ?site - site)
  )

  (:action restore-link
    :parameters (?cluster - cluster ?site - site)
    :precondition (and
      (standby-site ?cluster ?site)
    )
    :effect (and
      (link-restored ?cluster)
    )
  )

  (:action promote-primary
    :parameters (?cluster - cluster ?site - site)
    :precondition (and
      (standby-site ?cluster ?site)
      (link-restored ?cluster)
      (secondary-synced ?cluster ?site)
    )
    :effect (and
      (primary-promoted ?cluster ?site)
    )
  )

  (:action restart-core-service
    :parameters (?cluster - cluster ?service - service ?site - site)
    :precondition (and
      (core-role ?cluster ?service)
      (standby-site ?cluster ?site)
      (primary-promoted ?cluster ?site)
      (can-host ?service ?site)
    )
    :effect (and
      (core-online ?cluster ?service ?site)
    )
  )

  (:action restart-edge-service
    :parameters (?cluster - cluster ?edge - service ?core - service ?site - site)
    :precondition (and
      (edge-role ?cluster ?edge)
      (core-role ?cluster ?core)
      (standby-site ?cluster ?site)
      (core-online ?cluster ?core ?site)
      (can-host ?edge ?site)
    )
    :effect (and
      (edge-online ?cluster ?edge ?site)
    )
  )

  (:action cutover-traffic
    :parameters (?cluster - cluster ?gateway - gateway ?edge - service ?site - site)
    :precondition (and
      (uses-gateway ?cluster ?gateway)
      (edge-role ?cluster ?edge)
      (standby-site ?cluster ?site)
      (edge-online ?cluster ?edge ?site)
      (link-restored ?cluster)
    )
    :effect (and
      (traffic-cutover ?cluster ?gateway ?site)
      (stabilized ?cluster)
    )
  )

  (:action rebuild-replica
    :parameters (?cluster - cluster ?replica - replica ?failed - site ?standby - site)
    :precondition (and
      (failed-site ?cluster ?failed)
      (standby-site ?cluster ?standby)
      (stabilized ?cluster)
      (rebuild-target ?cluster ?replica ?failed)
    )
    :effect (and
      (rebuilt ?cluster ?replica ?failed)
    )
  )
)
