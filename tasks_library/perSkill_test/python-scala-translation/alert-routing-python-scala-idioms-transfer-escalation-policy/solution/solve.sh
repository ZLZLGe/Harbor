#!/bin/bash
set -euo pipefail

output_path="${OUTPUT_PATH:-/root/AlertRouting.scala}"

cat <<'EOF' > "$output_path"
sealed trait Severity {
  def label: String
}

object Severity {
  case object Info extends Severity {
    val label: String = "info"
  }

  case object Warning extends Severity {
    val label: String = "warning"
  }

  case object Critical extends Severity {
    val label: String = "critical"
  }

  val values: Vector[Severity] = Vector(Info, Warning, Critical)

  def fromLabel(value: String): Option[Severity] =
    values.find(_.label == AlertRouting.normalizeToken(value))
}

sealed trait DeliveryChannel {
  def label: String
}

object DeliveryChannel {
  case object Chat extends DeliveryChannel {
    val label: String = "chat"
  }

  case object Email extends DeliveryChannel {
    val label: String = "email"
  }

  case object Pager extends DeliveryChannel {
    val label: String = "pager"
  }

  case object Phone extends DeliveryChannel {
    val label: String = "phone"
  }

  val values: Vector[DeliveryChannel] = Vector(Chat, Email, Pager, Phone)

  def fromLabel(value: String): Option[DeliveryChannel] =
    values.find(_.label == AlertRouting.normalizeToken(value))
}

final case class ScheduleWindow(
  name: String,
  startHour: Int,
  endHour: Int,
  primary: Vector[String],
  secondary: Vector[String] = Vector.empty,
  afterHours: Boolean = false
) {
  def includes(hour: Int): Boolean = {
    val normalized = ((hour % 24) + 24) % 24
    if (startHour == endHour) true
    else if (startHour < endHour) normalized >= startHour && normalized < endHour
    else normalized >= startHour || normalized < endHour
  }

  def targetsFor(severity: Severity): Vector[String] = severity match {
    case Severity.Critical => AlertRouting.deduplicate(primary ++ secondary)
    case _ => AlertRouting.deduplicate(primary)
  }
}

final case class EscalationPolicy(
  initialChannel: DeliveryChannel,
  repeatChannel: Option[DeliveryChannel] = None,
  repeatAfterMinutes: Option[Int] = None,
  fallbackChannel: Option[DeliveryChannel] = None,
  suppressAfterHours: Boolean = false
)

final case class Alert(
  service: String,
  severity: Severity,
  createdHour: Int,
  tags: Vector[String] = Vector.empty,
  metadata: Map[String, String] = Map.empty,
  summary: String = ""
)

final case class EscalationStep(
  channel: DeliveryChannel,
  targets: Vector[String],
  delayMinutes: Int,
  note: String
)

final case class RoutingDecision(
  service: String,
  severity: Severity,
  activeWindow: Option[String],
  steps: Vector[EscalationStep],
  fallbackUsed: Boolean,
  dedupKey: String
)

final case class ServicePolicy(
  service: String,
  windows: Vector[ScheduleWindow],
  policies: Map[Severity, EscalationPolicy],
  fallbackTargets: Vector[String] = Vector.empty,
  tagOverrides: Map[String, DeliveryChannel] = Map.empty
) {
  def findWindow(hour: Int): Option[ScheduleWindow] =
    windows.find(_.includes(hour))
}

final class AlertRouter(val policies: Map[String, ServicePolicy]) {
  def resolveService(service: String): ServicePolicy =
    policies.getOrElse(AlertRouting.normalizeToken(service), policies("default"))

  def activeWindow(service: String, hour: Int): Option[ScheduleWindow] =
    resolveService(service).findWindow(hour)

  def route(alert: Alert): RoutingDecision = {
    val servicePolicy = resolveService(alert.service)
    val escalationPolicy =
      servicePolicy.policies.getOrElse(alert.severity, servicePolicy.policies(Severity.Warning))
    val activeWindow = servicePolicy.findWindow(alert.createdHour)
    val afterHours = activeWindow.forall(_.afterHours)
    val fallbackTargets = AlertRouting.deduplicate(servicePolicy.fallbackTargets)

    val overrideChannel = alert.tags.iterator
      .map(AlertRouting.normalizeToken)
      .collectFirst(Function.unlift(servicePolicy.tagOverrides.get))

    val baseTargets = activeWindow.map(_.targetsFor(alert.severity)).getOrElse(Vector.empty)
    val repeatTargets = activeWindow
      .map(window => AlertRouting.deduplicate(window.secondary))
      .filter(_.nonEmpty)
      .getOrElse(fallbackTargets)

    val tags = alert.tags.map(AlertRouting.normalizeToken).filter(_.nonEmpty).distinct.sorted

    val (steps, fallbackUsed) =
      if (escalationPolicy.suppressAfterHours && afterHours) {
        val digestChannel = escalationPolicy.fallbackChannel.getOrElse(escalationPolicy.initialChannel)
        Vector(EscalationStep(digestChannel, fallbackTargets, 0, "after-hours digest")) -> true
      } else {
        val usingFallbackTargets = activeWindow.isEmpty || baseTargets.isEmpty
        val chosenInitialChannel =
          if (usingFallbackTargets) escalationPolicy.fallbackChannel.getOrElse(overrideChannel.getOrElse(escalationPolicy.initialChannel))
          else overrideChannel.getOrElse(escalationPolicy.initialChannel)
        val chosenInitialTargets = if (usingFallbackTargets) fallbackTargets else baseTargets
        val firstStep = EscalationStep(
          chosenInitialChannel,
          chosenInitialTargets,
          0,
          if (overrideChannel.isDefined && !usingFallbackTargets) "tag override" else "initial"
        )
        val extraSteps = for {
          channel <- escalationPolicy.repeatChannel.toVector
          delay <- escalationPolicy.repeatAfterMinutes.toVector
          if repeatTargets.nonEmpty
        } yield EscalationStep(channel, repeatTargets, delay, "escalation")

        val fallbackHit = usingFallbackTargets || (repeatTargets == fallbackTargets && fallbackTargets.nonEmpty)
        (firstStep +: extraSteps).toVector -> fallbackHit
      }

    RoutingDecision(
      service = servicePolicy.service,
      severity = alert.severity,
      activeWindow = activeWindow.map(_.name),
      steps = steps,
      fallbackUsed = fallbackUsed,
      dedupKey = s"${servicePolicy.service}:${alert.severity.label}:${tags.mkString(",")}"
    )
  }

  def routeBatch(alerts: Iterable[Alert]): Vector[RoutingDecision] =
    alerts.iterator.map(route).toVector
}

object AlertRouting {
  def normalizeToken(value: String): String =
    value.trim.toLowerCase.split("\\s+").filter(_.nonEmpty).mkString(" ")

  def deduplicate(values: Seq[String]): Vector[String] =
    values.iterator
      .map(normalizeToken)
      .filter(_.nonEmpty)
      .foldLeft(Vector.empty[String]) { (acc, item) =>
        if (acc.contains(item)) acc else acc :+ item
      }

  val defaultPolicies: Map[String, ServicePolicy] = {
    val sharedPolicies = Map[Severity, EscalationPolicy](
      Severity.Info -> EscalationPolicy(
        initialChannel = DeliveryChannel.Chat,
        fallbackChannel = Some(DeliveryChannel.Email),
        suppressAfterHours = true
      ),
      Severity.Warning -> EscalationPolicy(
        initialChannel = DeliveryChannel.Chat,
        repeatChannel = Some(DeliveryChannel.Email),
        repeatAfterMinutes = Some(20),
        fallbackChannel = Some(DeliveryChannel.Phone)
      ),
      Severity.Critical -> EscalationPolicy(
        initialChannel = DeliveryChannel.Pager,
        repeatChannel = Some(DeliveryChannel.Phone),
        repeatAfterMinutes = Some(5),
        fallbackChannel = Some(DeliveryChannel.Phone)
      )
    )

    Map(
      "payments" -> ServicePolicy(
        service = "payments",
        windows = Vector(
          ScheduleWindow(
            name = "business",
            startHour = 8,
            endHour = 18,
            primary = Vector("maya", "nico"),
            secondary = Vector("payments-manager")
          ),
          ScheduleWindow(
            name = "overnight",
            startHour = 18,
            endHour = 8,
            primary = Vector("night-pay"),
            secondary = Vector("incident-commander"),
            afterHours = true
          )
        ),
        policies = sharedPolicies,
        fallbackTargets = Vector("payments-dispatch"),
        tagOverrides = Map(
          "vip" -> DeliveryChannel.Pager,
          "audit" -> DeliveryChannel.Email
        )
      ),
      "platform" -> ServicePolicy(
        service = "platform",
        windows = Vector(
          ScheduleWindow(
            name = "day",
            startHour = 9,
            endHour = 17,
            primary = Vector("infra-east", "infra-west"),
            secondary = Vector("infra-manager")
          ),
          ScheduleWindow(
            name = "overnight",
            startHour = 17,
            endHour = 9,
            primary = Vector("platform-night"),
            secondary = Vector("duty-director"),
            afterHours = true
          )
        ),
        policies = sharedPolicies,
        fallbackTargets = Vector("global-noc"),
        tagOverrides = Map("maintenance" -> DeliveryChannel.Email)
      ),
      "default" -> ServicePolicy(
        service = "default",
        windows = Vector.empty,
        policies = sharedPolicies,
        fallbackTargets = Vector("global-noc")
      )
    )
  }

  val defaultRouter: AlertRouter = new AlertRouter(defaultPolicies)

  def routeAlert(alert: Alert, policies: Map[String, ServicePolicy] = defaultPolicies): RoutingDecision =
    new AlertRouter(policies).route(alert)

  def routeBatch(alerts: Iterable[Alert], policies: Map[String, ServicePolicy] = defaultPolicies): Vector[RoutingDecision] =
    new AlertRouter(policies).routeBatch(alerts)

  def summarizeByChannel(decisions: Iterable[RoutingDecision]): Map[String, Int] =
    decisions.iterator
      .flatMap(_.steps.iterator)
      .foldLeft(Map.empty[String, Int]) { (acc, step) =>
        val label = step.channel.label
        acc.updated(label, acc.getOrElse(label, 0) + 1)
      }

  def escalationTargets(decision: RoutingDecision): Vector[String] =
    decision.steps.iterator
      .flatMap(_.targets.iterator)
      .map(normalizeToken)
      .filter(_.nonEmpty)
      .foldLeft(Vector.empty[String]) { (acc, target) =>
        if (acc.contains(target)) acc else acc :+ target
      }
}
EOF
