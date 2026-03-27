#!/bin/bash
set -euo pipefail

cat > /app/workspace/transfer3.scala <<'SCALA'
trait Plugin {
  def name: String
  def run(payload: String): String
}

final case class PluginResult(plugin: String, value: String)

final class EchoPlugin extends Plugin {
  override def name: String = "echo"
  override def run(payload: String): String = payload
}

final class UpperPlugin extends Plugin {
  override def name: String = "upper"
  override def run(payload: String): String = payload.toUpperCase
}

final class PluginRegistry private () {
  private val plugins = scala.collection.mutable.Map.empty[String, Plugin]

  def register(plugin: Plugin): Unit = {
    plugins.update(plugin.name, plugin)
  }

  def execute(pluginName: String, payload: String): PluginResult = {
    val p = plugins(pluginName)
    PluginResult(pluginName, p.run(payload))
  }
}

object PluginRegistry {
  def empty: PluginRegistry = new PluginRegistry()

  def fromDefaults(): PluginRegistry = {
    val registry = empty
    registry.register(new EchoPlugin())
    registry.register(new UpperPlugin())
    registry
  }
}
SCALA
