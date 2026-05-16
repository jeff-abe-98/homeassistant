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
    timeout: float = 30.0


@dataclass
class WhisperConfig:
    model: str = "large-v3"
    device: str = "auto"
    compute_type: str = "auto"


@dataclass
class GoogleConfig:
    credentials_file: str = "config/google_credentials.json"
    token_file: str = "config/google_token.json"
    scopes: list = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/tasks",
    ])


@dataclass
class SpotifyUserConfig:
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8888/callback"
    token_file: str = ""


@dataclass
class SpotifyConfig:
    owner: SpotifyUserConfig = field(default_factory=SpotifyUserConfig)
    emily: SpotifyUserConfig = field(default_factory=SpotifyUserConfig)


@dataclass
class CtaConfig:
    api_key: str = ""
    stop_id_ohare: int = 30238
    stop_id_forest_park: int = 30239


@dataclass
class WeatherConfig:
    api_key: str = ""
    location: str = "Chicago, IL"
    units: str = "imperial"


@dataclass
class AndroidTvConfig:
    host: str = ""
    port: int = 6466
    cert_file: str = "config/androidtv_cert.pem"
    key_file: str = "config/androidtv_key.pem"


@dataclass
class WakeWordConfig:
    model: str = "hey_jarvis"
    threshold: float = 0.5
    # Require this many consecutive frames above threshold before firing.
    # At 80ms/frame, min_activation_count=3 means ~240ms of sustained detection.
    # Higher values cut false positives; lower values improve responsiveness.
    min_activation_count: int = 3
    # Seconds to ignore further detections after one fires.
    # Prevents double-triggering on the same utterance.
    cooldown_seconds: float = 2.0


@dataclass
class PiperConfig:
    model_path: str = "pi/tts/models/en_US-lessac-medium.onnx"
    use_cuda: bool = False


@dataclass
class LoggingConfig:
    log_dir: str = "logs"
    log_file: str = "homeassistant.log"
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5
    level: str = "INFO"


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
    wake_word: WakeWordConfig = field(default_factory=WakeWordConfig)
    tts: PiperConfig = field(default_factory=PiperConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _spotify_user(d: dict, token_file: str = "", default_redirect: str = "http://localhost:8888/callback") -> SpotifyUserConfig:
    return SpotifyUserConfig(
        client_id=d.get("client_id", ""),
        client_secret=d.get("client_secret", ""),
        redirect_uri=d.get("redirect_uri", default_redirect),
        token_file=token_file,
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
    wkw = raw.get("wake_word", {})
    tts = raw.get("tts", {})
    log = raw.get("logging", {})
    users_raw = raw.get("users", {})

    return AppConfig(
        server=ServerConfig(
            host=srv.get("host", "0.0.0.0"),
            port=int(srv.get("port", 8000)),
        ),
        ollama=OllamaConfig(
            host=oll.get("host", "http://localhost:11434"),
            model=oll.get("model", "llama3.1:8b-instruct-q4_K_M"),
            timeout=float(oll.get("timeout", 30.0)),
        ),
        whisper=WhisperConfig(
            model=whi.get("model", "large-v3"),
            device=whi.get("device", "auto"),
            compute_type=whi.get("compute_type", "auto"),
        ),
        google=GoogleConfig(
            credentials_file=goo.get("credentials_file", "config/google_credentials.json"),
            token_file=goo.get("token_file", "config/google_token.json"),
            scopes=goo.get("scopes", [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/tasks",
            ]),
        ),
        spotify=SpotifyConfig(
            owner=_spotify_user(
                spo.get("owner", {}),
                token_file=users_raw.get("owner", {}).get(
                    "spotify_token_file", "config/spotify_token_owner.json"
                ),
                default_redirect="http://localhost:8888/callback",
            ),
            emily=_spotify_user(
                spo.get("emily", {}),
                token_file=users_raw.get("emily", {}).get(
                    "spotify_token_file", "config/spotify_token_emily.json"
                ),
                default_redirect="http://localhost:8889/callback",
            ),
        ),
        cta=CtaConfig(
            api_key=cta.get("api_key", ""),
            stop_id_ohare=int(cta.get("stop_id_ohare", 30238)),
            stop_id_forest_park=int(cta.get("stop_id_forest_park", 30239)),
        ),
        weather=WeatherConfig(
            api_key=wea.get("api_key", ""),
            location=wea.get("location", "Chicago, IL"),
            units=wea.get("units", "imperial"),
        ),
        androidtv=AndroidTvConfig(
            host=atv.get("host", ""),
            port=int(atv.get("port", 6466)),
            cert_file=atv.get("cert_file", "config/androidtv_cert.pem"),
            key_file=atv.get("key_file", "config/androidtv_key.pem"),
        ),
        wake_word=WakeWordConfig(
            model=wkw.get("model", "hey_jarvis"),
            threshold=float(wkw.get("threshold", 0.5)),
            min_activation_count=int(wkw.get("min_activation_count", 3)),
            cooldown_seconds=float(wkw.get("cooldown_seconds", 2.0)),
        ),
        tts=PiperConfig(
            model_path=tts.get("model_path", "pi/tts/models/en_US-lessac-medium.onnx"),
            use_cuda=bool(tts.get("use_cuda", False)),
        ),
        logging=LoggingConfig(
            log_dir=log.get("log_dir", "logs"),
            log_file=log.get("log_file", "homeassistant.log"),
            max_bytes=int(log.get("max_bytes", 10 * 1024 * 1024)),
            backup_count=int(log.get("backup_count", 5)),
            level=log.get("level", "INFO"),
        ),
    )
