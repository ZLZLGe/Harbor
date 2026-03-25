#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/EventNormalizer.scala
sealed trait EventKind {
  def value: String
}

object EventKind {
  case object Login extends EventKind {
    val value: String = "login"
  }

  case object DataAccess extends EventKind {
    val value: String = "data_access"
  }

  case object ConfigChange extends EventKind {
    val value: String = "config_change"
  }

  case object Other extends EventKind {
    val value: String = "other"
  }
}

final case class AuditEvent(
  actor: Option[String],
  action: String,
  resource: Option[String] = None,
  tags: Seq[String] = Seq.empty,
  metadata: Option[Map[String, String]] = None
) {
  def withMetadata(entries: (String, String)*): AuditEvent =
    copy(metadata = Some(EventNormalizer.mergeMetadata(metadata, Some(entries.toMap))))
}

final case class NormalizedEvent(
  actor: String,
  action: String,
  resource: String,
  kind: EventKind,
  tags: Seq[String] = Seq.empty,
  metadata: Map[String, String] = Map.empty
) {
  def withMetadata(entries: (String, String)*): NormalizedEvent =
    copy(metadata = EventNormalizer.mergeMetadata(Some(metadata), Some(entries.toMap)))
}

trait BaseNormalizer[-A, +B] {
  def normalize(value: A): B

  def normalizeBatch(values: IterableOnce[A]): Iterator[B] =
    values.iterator.map(normalize)
}

object EventNormalizer {
  def makeFieldNormalizer(
    aliases: Map[String, String] = Map.empty,
    defaultValue: Option[String] = None,
    transform: String => String = identity
  ): Option[String] => Option[String] = {
    val normalizedAliases = aliases.iterator.map { case (key, value) =>
      key.trim.toLowerCase -> value.trim.toLowerCase
    }.toMap

    value =>
      value
        .map(_.trim)
        .filter(_.nonEmpty)
        .map { cleaned =>
          normalizedAliases.getOrElse(cleaned.toLowerCase, cleaned.toLowerCase)
        }
        .map(transform)
        .orElse(defaultValue)
  }

  def mergeMetadata(sources: Option[Map[String, String]]*): Map[String, String] =
    sources.iterator.flatten.foldLeft(Map.empty[String, String])(_ ++ _)

  def normalizeEvents(
    events: IterableOnce[AuditEvent],
    normalizer: Option[AuditEventNormalizer] = None
  ): Iterator[NormalizedEvent] =
    normalizer.getOrElse(new AuditEventNormalizer()).normalizeBatch(events)
}

final class AuditEventNormalizer(
  actorAliases: Map[String, String] = Map.empty,
  resourceAliases: Map[String, String] = Map.empty,
  baseMetadata: Map[String, String] = Map.empty
) extends BaseNormalizer[AuditEvent, NormalizedEvent] {
  private val actorNormalizer =
    EventNormalizer.makeFieldNormalizer(actorAliases, defaultValue = Some("system"))
  private val resourceNormalizer =
    EventNormalizer.makeFieldNormalizer(resourceAliases, defaultValue = Some("unknown-resource"))
  private val actionNormalizer =
    EventNormalizer.makeFieldNormalizer(transform = _.replace(" ", "_"))

  def inferKind(action: String): EventKind = {
    val normalized = actionNormalizer(Some(action)).getOrElse("unknown-action")
    normalized match {
      case "login" | "sign_in" => EventKind.Login
      case value if value.startsWith("read_") || value.startsWith("export_") || value == "download" || value == "view" =>
        EventKind.DataAccess
      case value if value.startsWith("config_") || value.startsWith("rotate_") || value.endsWith("_policy") =>
        EventKind.ConfigChange
      case _ => EventKind.Other
    }
  }

  override def normalize(event: AuditEvent): NormalizedEvent = {
    val normalizedActor = actorNormalizer(event.actor).getOrElse("system")
    val normalizedResource = resourceNormalizer(event.resource).getOrElse("unknown-resource")
    val normalizedAction = actionNormalizer(Some(event.action)).getOrElse("unknown-action")
    val normalizedTags = event.tags.iterator.map(_.trim).filter(_.nonEmpty).map(_.toLowerCase).toSet.toVector.sorted
    val mergedMetadata = EventNormalizer.mergeMetadata(Some(baseMetadata), event.metadata)

    NormalizedEvent(
      actor = normalizedActor,
      action = normalizedAction,
      resource = normalizedResource,
      kind = inferKind(normalizedAction),
      tags = normalizedTags,
      metadata = mergedMetadata
    )
  }

  override def normalizeBatch(values: IterableOnce[AuditEvent]): Iterator[NormalizedEvent] =
    values.iterator.map(normalize)

  def withMetadata(entries: (String, String)*): AuditEventNormalizer =
    new AuditEventNormalizer(
      actorAliases = actorAliases,
      resourceAliases = resourceAliases,
      baseMetadata = baseMetadata ++ entries.toMap
    )
}
EOF
