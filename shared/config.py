from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "llama3.1:8b-instruct-q4_K_M"


@dataclass
class WhisperConfig:
    model: str = "large-v3"
    device: str = "auto"
    compute_type: str = "auto"


@dataclass
class GoogleConfig:
    credentials_file: str = "config/google_credentials.json"


@dataclass
class SpotifyUserConfig:
    client_id: str = ""
    client_secret: str = ""


@dataclass
class SpotifyConfig:
    owner: SpotifyUserConfig = field(default_factory=SpotifyUserConfig)
    emily: SpotifyUserConfig = field(default_factory=SpotifyUserConfig)


@dataclass
class CtaConfig:
    api_key: str = ""


@dataclass
class WeatherConfig:
    api_key: str = ""
    location: str = "Chicago, IL"


@dataclass
class AndroidTvConfig:
    host: str = ""
    port: int = 6466


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    google: GoogleConfig = field(default_factory=GoogleConfig)
    spotify: SpotifyConfig = field(default_factory=SpotifyConfig)
    cta: CtaConfig = field(default_factory=CtaConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    androidtv: AndroidTvConfig = field(default_factory=AndroidTvConfig)


def _spotify_user(d: dict) -> SpotifyUserConfig:
    return SpotifyUserConfig(
        client_id=d.get("client_id", ""),
        client_secret=d.get("client_secret", ""),
    )


def load(path: str | None = None) -> AppConfig:
    if path is None:
        path = os.environ.get(
            "SETTINGS_PATH",
            str(Path(__file__).parent.parent / "config" / "settings.yaml"),
        )

    raw: dict = {}
    settings_path = Path(path)
    if settings_path.exists():
        with settings_path.open() as f:
            raw = yaml.safe_load(f) or {}

    srv = raw.get("server", {})
    oll = raw.get("ollama", {})
    whi = raw.get("whisper", {})
    goo = raw.get("google", {})
    spo = raw.get("spotify", {})
    cta = raw.get("cta", {})
    wea = raw.get("weather", {})
    atv = raw.get("androidtv", {})

    return AppConfig(
        server=ServerConfig(
            host=srv.get("host", "0.0.0.0"),
            port=int(srv.get("port", 8000)),
        ),
        ollama=OllamaConfig(
            host=oll.get("host", "http://localhost:11434"),
            model=oll.get("model", "llama3.1:8b-instruct-q4_K_M"),
        ),
        whisper=WhisperConfig(
            model=whi.get("model", "large-v3"),
            device=whi.get("device", "auto"),
            compute_type=whi.get("compute_type", "auto"),
        ),
        google=GoogleConfig(
            credentials_file=goo.get("credentials_file", "config/google_credentials.json"),
        ),
        spotify=SpotifyConfig(
            owner=_spotify_user(spo.get("owner", {})),
            emily=_spotify_user(spo.get("emily", {})),
        ),
        cta=CtaConfig(
            api_key=cta.get("api_key", ""),
        ),
        weather=WeatherConfig(
            api_key=wea.get("api_key", ""),
            location=wea.get("location", "Chicago, IL"),
        ),
        androidtv=AndroidTvConfig(
            host=atv.get("host", ""),
            port=int(atv.get("port", 6466)),
        ),
    )
