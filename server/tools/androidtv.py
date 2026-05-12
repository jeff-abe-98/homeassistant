"""Android TV control tool — androidtvremote2 over port 6466, no ADB needed."""

from __future__ import annotations

import shared.config as cfg_module
from server.tools.base import BaseTool

_KEYCODE_POWER_ON = "KEYCODE_WAKEUP"
_KEYCODE_POWER_OFF = "KEYCODE_SLEEP"

_UNCONFIGURED_HOSTS = {"", "192.168.x.x"}

# Friendly name → Android package name for common TV apps.
_APP_PACKAGES: dict[str, str] = {
    "spotify": "com.spotify.tv.android",
    "netflix": "com.netflix.ninja",
    "youtube": "com.google.android.youtube.tv",
    "youtube tv": "com.google.android.youtube.tvunplugged",
    "hulu": "com.hulu.plus",
    "disney+": "com.disney.disneyplus",
    "disney plus": "com.disney.disneyplus",
    "hbo max": "com.hbo.hbonow",
    "max": "com.hbo.hbonow",
    "prime video": "com.amazon.amazonvideo.livingroom",
    "amazon prime": "com.amazon.amazonvideo.livingroom",
}


def _resolve_package(app: str) -> str:
    """Return a package name for *app*.

    If *app* looks like a package already (contains a dot) return it as-is.
    Otherwise do a case-insensitive lookup in the friendly-name table.
    Raises ValueError if the name is unknown.
    """
    if "." in app:
        return app
    key = app.strip().lower()
    if key in _APP_PACKAGES:
        return _APP_PACKAGES[key]
    known = ", ".join(sorted(_APP_PACKAGES))
    raise ValueError(f"Unknown app '{app}'. Known apps: {known}.")


def _launch_intent(package: str) -> str:
    """Build an Android intent URI that launches a TV app by package name."""
    return (
        f"intent:#Intent;"
        f"action=android.intent.action.MAIN;"
        f"category=android.intent.category.LEANBACK_LAUNCHER;"
        f"launchFlags=0x10000000;"
        f"package={package};end"
    )


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
        "Can turn the TV on or off, and launch apps by name. "
        "Use for: 'turn on the TV', 'turn off the TV', 'open Netflix', 'launch Spotify on the TV', "
        "'put on YouTube', 'open Disney Plus'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["power_on", "power_off", "launch_app"],
                "description": (
                    "Turn the TV on (power_on), put it to sleep (power_off), "
                    "or open an app (launch_app)."
                ),
            },
            "app": {
                "type": "string",
                "description": (
                    "App to launch. Use the friendly name (spotify, netflix, youtube, hulu, "
                    "disney+, max, prime video) or a full Android package name like "
                    "com.netflix.ninja. Only required when action is launch_app."
                ),
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

        action = params.get("action", "power_on")

        if action == "launch_app":
            app_name = params.get("app", "")
            if not app_name:
                return "Which app should I open? Say something like 'open Netflix' or 'launch Spotify'."
            try:
                package = _resolve_package(app_name)
            except ValueError as exc:
                return str(exc)

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
            if action == "power_on":
                atv.send_key_command(_KEYCODE_POWER_ON)
                return "TV is on."
            elif action == "power_off":
                atv.send_key_command(_KEYCODE_POWER_OFF)
                return "TV is off."
            else:  # launch_app
                atv.send_launch_app(_launch_intent(package))
                friendly = app_name.title() if "." not in app_name else package
                return f"Opening {friendly} on the TV."
        finally:
            atv.disconnect()
