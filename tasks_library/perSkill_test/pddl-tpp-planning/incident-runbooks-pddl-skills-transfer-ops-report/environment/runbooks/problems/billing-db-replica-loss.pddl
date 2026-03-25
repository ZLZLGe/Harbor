(define (problem billing-db-replica-loss)
  (:domain incident-runbooks)
  (:objects
    billing-db-replica-loss - incident
    billing-cluster - cluster)
  (:init
    (alert-open billing-db-replica-loss)
    (needs-failover billing-db-replica-loss billing-cluster))
  (:goal
    (resolved billing-db-replica-loss)))
