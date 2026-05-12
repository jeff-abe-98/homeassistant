"""Android TV control tool — androidtvremote2 over port 6466, no ADB needed."""

from __future__ import annotations

import shared.config as cfg_module
from server.tools.base import BaseTool

_KEYCODE_POWER_ON = "KEYCODE_WAKEUP"
_KEYCODE_POWER_OFF = "KEYCODE_SLEEP"

_UNCONFIGURED_HOSTS = {"", "192.168.x.x"}


def _is_configured(cfg) -> bool:
    return cfg.androidtv.host not in _UNCONFIGURED_HOSTS


async def _connect(atv_cfg):
    """Return a connected AndroidTVRemote instance.

    Generates the TLS cert pair on first call.  Raises CannotConnect or
    InvalidAuth (from androidtvremote2) if the TV is unreachable or unpaired.
    """
    from androidtvremote2 import AndroidTVRemote  # lazy — not installed on Pi

    atv = AndroidTVRemote(
        client_name="HomeAssistant",
        certfile=atv_cfg.cert_file,
        keyfile=atv_cfg.key_file,
        host=atv_cfg.host,
        port=atv_cfg.port,
    )
    await atv.async_generate_cert_if_missing()
    await atv.async_connect()
    return atv


class AndroidTvTool(BaseTool):
    name = "androidtv_control"
    description = (
        "Control the Android TV in the living room. "
        "Can turn the TV on or off. "
        "Use for: 'turn on the TV', 'turn off the TV', 'wake up the TV', 'power off the TV'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["power_on", "power_off"],
                "description": "Turn the TV on (power_on) or put it to sleep (power_off).",
            },
        },
        "required": ["action"],
    }

    async def run(self, params: dict, user: str) -> str:
        cfg = cfg_module.load()

        if not _is_configured(cfg):
            return (
                "Android TV isn't set up yet — I need the TV's IP address. "
                "Set androidtv.host in config/settings.yaml."
            )

        try:
            atv = await _connect(cfg.androidtv)
        except Exception as exc:
            name = type(exc).__name__
            if "InvalidAuth" in name or "Auth" in name:
                return (
                    "The TV rejected the connection. It may need to be paired first. "
                    "Run: python -m server.tools.androidtv_pair"
                )
            if "CannotConnect" in name or "Connect" in name or "Timeout" in name:
                return "I couldn't reach the TV. Make sure it's on and on the same network."
            return f"Unexpected error connecting to the TV: {exc}"

        try:
            action = params.get("action", "power_on")
            if action == "power_on":
                atv.send_key_command(_KEYCODE_POWER_ON)
                return "TV is on."
            else:
                atv.send_key_command(_KEYCODE_POWER_OFF)
                return "TV is off."
        finally:
            atv.disconnect()
