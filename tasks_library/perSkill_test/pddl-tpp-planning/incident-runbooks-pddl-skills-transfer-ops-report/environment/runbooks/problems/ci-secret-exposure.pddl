(define (problem ci-secret-exposure)
  (:domain incident-runbooks)
  (:objects
    ci-secret-exposure - incident
    ci-bot-token - secret)
  (:init
    (alert-open ci-secret-exposure)
    (needs-secret-rotation ci-secret-exposure ci-bot-token)
    (secret-access ci-bot-token))
  (:goal
    (resolved ci-secret-exposure)))
