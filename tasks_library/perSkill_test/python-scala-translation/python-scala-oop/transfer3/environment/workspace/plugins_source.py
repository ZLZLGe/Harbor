from dataclasses import dataclass


class Plugin:
    def name(self) -> str:
        raise NotImplementedError

    def run(self, payload: str) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class PluginResult:
    plugin: str
    value: str


class EchoPlugin(Plugin):
    def name(self) -> str:
        return "echo"

    def run(self, payload: str) -> str:
        return payload


class UpperPlugin(Plugin):
    def name(self) -> str:
        return "upper"

    def run(self, payload: str) -> str:
        return payload.upper()


class PluginRegistry:
    def __init__(self):
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin):
        self._plugins[plugin.name()] = plugin

    def execute(self, plugin_name: str, payload: str) -> PluginResult:
        p = self._plugins[plugin_name]
        return PluginResult(plugin_name, p.run(payload))

    @classmethod
    def from_defaults(cls) -> "PluginRegistry":
        r = cls()
        r.register(EchoPlugin())
        r.register(UpperPlugin())
        return r
