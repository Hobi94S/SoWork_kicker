from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from .client import build_client
from .config import SoWorkKickerConfig
from .engine import VerificationEngine


def _configure_logging() -> logging.Logger:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    return logging.getLogger('sowork-kicker')


def run_checks(config: SoWorkKickerConfig, *, logger: logging.Logger | None = None) -> list[Any]:
    client = build_client(config)
    engine = VerificationEngine(
        client,
        message_template=config.verification_message,
        timeout_seconds=config.response_timeout_seconds,
        simulation=config.simulation,
    )
    users = [
        user for user in client.get_online_users()
        if str(user.get('user_id') or user.get('id') or '').strip() not in set(config.exempt_users)
    ]
    results = [engine.run_single_user(user) for user in users]
    if logger:
        logger.info('Verificações concluídas: %s usuários avaliados.', len(results))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='SoWork Kicker: verificação por mensagem e desconexão por ausência de resposta.')
    parser.add_argument('--env-file', default='.env', help='Arquivo .env com as configurações do bot.')
    parser.add_argument('--real', action='store_true', help='Ativa a desconexão real; por padrão o modo é simulação.')
    parser.add_argument('--simulate', action='store_true', help='Força o modo de simulação mesmo quando a desconexão real estiver disponível.')
    args = parser.parse_args(argv)
    logger = _configure_logging()
    config = SoWorkKickerConfig.from_env(args.env_file)
    config.simulation = not args.real if not args.simulate else True
    try:
        results = run_checks(config, logger=logger)
        if results:
            logger.info(json.dumps([result.__dict__ for result in results], default=str, ensure_ascii=False))
        return 0
    except Exception as exc:  # pragma: no cover - CLI guardrail
        logger.exception('Falha durante a execução do SoWork Kicker: %s', exc)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
