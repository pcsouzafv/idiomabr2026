from __future__ import annotations

import logging
from typing import Optional

import requests
from fastapi import HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.services.session_store import get_session_store

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        ip = xff.split(",")[0].strip()
        if ip:
            return ip

    xrip = (request.headers.get("x-real-ip") or "").strip()
    if xrip:
        return xrip

    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def enforce_rate_limit(*, scope: str, identifier: str, limit: int, window_seconds: int) -> None:
    if limit <= 0:
        return
    key = f"rate-limit:{scope}:{identifier}"
    store = get_session_store()
    data = store.get(key) or {}

    try:
        count = int(data.get("count", 0))
    except Exception:
        count = 0

    count += 1
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Aguarde alguns minutos e tente novamente.",
        )

    store.set(key, {"count": count}, ttl_seconds=float(window_seconds))


def enforce_register_captcha(*, captcha_token: Optional[str], client_ip: str) -> None:
    settings = get_settings()
    if settings.environment.lower() != "production":
        return

    secret = (settings.turnstile_secret_key or "").strip()
    if not secret:
        # Allow registration without captcha when Turnstile isn't configured yet.
        # Rate-limits still apply and captcha becomes enforced automatically once the secret is provided.
        logger.warning("Turnstile not configured (TURNSTILE_SECRET_KEY empty). Skipping captcha validation.")
        return

    if not (captcha_token or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha obrigatorio",
        )

    _verify_turnstile_token(
        captcha_token=captcha_token or "",
        client_ip=client_ip,
        settings=settings,
    )


def _verify_turnstile_token(*, captcha_token: str, client_ip: str, settings: Settings) -> None:
    payload = {
        "secret": settings.turnstile_secret_key,
        "response": captcha_token,
    }
    if client_ip and client_ip != "unknown":
        payload["remoteip"] = client_ip

    try:
        response = requests.post(
            settings.turnstile_verify_url,
            data=payload,
            timeout=8,
        )
        response.raise_for_status()
        body = response.json()
    except Exception:
        logger.exception("Falha ao validar captcha Turnstile")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nao foi possivel validar o captcha no momento. Tente novamente.",
        )

    if not bool(body.get("success")):
        logger.warning(
            "Captcha Turnstile rejeitado. errors=%s",
            body.get("error-codes"),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha na validacao do captcha",
        )
