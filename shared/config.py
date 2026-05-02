from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "llama3.1:8b-instruct-q4_K_M"


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
class CTAConfig:
    api_key: str = ""


@dataclass
class WeatherConfig:
    api_key: str = ""
    location: str = "Chicago, IL"


@dataclass
class AndroidTVConfig:
    host: str = ""
    port: int = 6466


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    google: GoogleConfig = field(default_factory=GoogleConfig)
    spotify: SpotifyConfig = field(default_factory=SpotifyConfig)
    cta: CTAConfig = field(default_factory=CTAConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    androidtv: AndroidTVConfig = field(default_factory=AndroidTVConfig)


def load_config(path: Path = _DEFAULT_CONFIG_PATH) -> AppConfig:
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    spotify_data = data.get("spotify", {})

    return AppConfig(
        server=ServerConfig(**data.get("server", {})),
        ollama=OllamaConfig(**data.get("ollama", {})),
        google=GoogleConfig(**data.get("google", {})),
        spotify=SpotifyConfig(
            owner=SpotifyUserConfig(**spotify_data.get("owner", {})),
            emily=SpotifyUserConfig(**spotify_data.get("emily", {})),
        ),
        cta=CTAConfig(**data.get("cta", {})),
        weather=WeatherConfig(**data.get("weather", {})),
        androidtv=AndroidTVConfig(**data.get("androidtv", {})),
    )
