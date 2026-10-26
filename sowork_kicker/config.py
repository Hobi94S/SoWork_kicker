from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"\'')
    return values


def _env(key: str, default: Any = "", *, prefix: str = "SOWORK") -> Any:
    return os.environ.get(f"{prefix}_{key}", default)


@dataclass
class SoWorkKickerConfig:
    verification_message: str = (
        "Por favor, responda esta mensagem para confirmar que continua conectado ao ambiente."
    )
    response_timeout_seconds: int = 120
    simulation: bool = True
    exempt_users: list[str] = field(default_factory=list)
    selection_criteria: dict[str, Any] = field(default_factory=lambda: {"online_only": True})
    app_url: str = "https://app.sowork.com"
    environment_name: str = "SoWork"
    output_dir: Path = Path("output")
    log_dir: Path = Path("logs")
    profile_dir: Path = Path("profiles/sowork-kicker")

    @classmethod
    def from_env(cls, env_path: str = ".env") -> "SoWorkKickerConfig":
        values = _load_dotenv(Path(env_path))
        values.update({key: value for key, value in os.environ.items() if key.startswith("SOWORK_")})

        def get(name: str, default: Any, *, cast: type | None = None):
            value = values.get(f"SOWORK_{name}", default)
            if cast is None:
                return value
            if cast is bool:
                return str(value).strip().lower() in {"1", "true", "yes", "on"}
            if cast is int:
                return int(value)
            if cast is list:
                if value in (None, ""):
                    return []
                return [part.strip() for part in str(value).split(",") if part.strip()]
            return cast(value)

        exempt = get("EXEMPT_USERS", "", cast=list)
        config = cls(
            verification_message=get("VERIFICATION_MESSAGE", cls.verification_message),
            response_timeout_seconds=get("RESPONSE_TIMEOUT_SECONDS", cls.response_timeout_seconds, cast=int),
            simulation=get("SIMULATION", str(cls.simulation), cast=bool),
            exempt_users=exempt,
            selection_criteria={
                "online_only": get("ONLINE_ONLY", "true", cast=bool),
                "require_connected": get("REQUIRE_CONNECTED", "true", cast=bool),
            },
            app_url=get("APP_URL", cls.app_url),
            environment_name=get("ENVIRONMENT_NAME", cls.environment_name),
            output_dir=Path(get("OUTPUT_DIR", str(cls.output_dir))).expanduser(),
            log_dir=Path(get("LOG_DIR", str(cls.log_dir))).expanduser(),
            profile_dir=Path(get("PROFILE_DIR", str(cls.profile_dir))).expanduser(),
        )
        if config.response_timeout_seconds <= 0:
            raise ValueError("SOWORK_RESPONSE_TIMEOUT_SECONDS deve ser maior que zero.")
        return config
