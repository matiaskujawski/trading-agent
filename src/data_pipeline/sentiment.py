"""Indicadores de sentimiento/contexto de mercado amplio (ver CONTEXTO.md).
Se usan como contexto de bajo peso para el LLM -- nunca como señal principal
ni gatillo de entrada, esa sigue siendo siempre la técnica sobre precio.

Solo aplica a cripto: forex no tiene equivalente de estos indicadores.
"""

import json
import urllib.request
from datetime import date

import ccxt

FUNDING_RATE_TIMEOUT_S = 10

# Halvings de Bitcoin conocidos + próximo estimado. Es un evento de calendario,
# no hace falta ninguna fuente de datos externa. Solo 4 ocurrencias históricas:
# se trata como contexto histórico blando, no como una regla predictiva fuerte.
HALVING_DATES = [date(2012, 11, 28), date(2016, 7, 9), date(2020, 5, 11), date(2024, 4, 20)]
NEXT_HALVING_ESTIMATE = date(2028, 4, 20)  # aproximado -- se ajusta cuando se acerque la fecha real


def fetch_fear_greed_index() -> dict:
    with urllib.request.urlopen("https://api.alternative.me/fng/?limit=1", timeout=FUNDING_RATE_TIMEOUT_S) as r:
        entry = json.load(r)["data"][0]
    return {"valor": int(entry["value"]), "clasificacion": entry["value_classification"]}


def fetch_btc_dominance() -> float:
    with urllib.request.urlopen("https://api.coingecko.com/api/v3/global", timeout=FUNDING_RATE_TIMEOUT_S) as r:
        data = json.load(r)["data"]
    return round(data["market_cap_percentage"]["btc"], 2)


def fetch_funding_rate(symbol: str = "BTC/USDT:USDT", exchange_id: str = "binance") -> float:
    exchange = getattr(ccxt, exchange_id)()
    return exchange.fetch_funding_rate(symbol)["fundingRate"]


def halving_context(today: date | None = None) -> dict:
    today = today or date.today()
    last_halving = max(d for d in HALVING_DATES if d <= today)
    return {
        "dias_desde_ultimo_halving": (today - last_halving).days,
        "dias_hasta_proximo_halving_estimado": (NEXT_HALVING_ESTIMATE - today).days,
    }


def build_sentiment_context() -> dict:
    """Junta todo en un solo dict compacto para meter en el resumen de mercado.
    Si alguna fuente falla (caída, timeout), esa clave queda ausente en vez de
    tirar abajo todo el ciclo de decisión -- estas señales son de apoyo, no
    críticas para poder operar."""
    context = {}

    try:
        context["fear_greed"] = fetch_fear_greed_index()
    except Exception as e:
        context["fear_greed_error"] = str(e)

    try:
        context["btc_dominance_pct"] = fetch_btc_dominance()
    except Exception as e:
        context["btc_dominance_error"] = str(e)

    try:
        context["btc_funding_rate"] = fetch_funding_rate()
    except Exception as e:
        context["funding_rate_error"] = str(e)

    context.update(halving_context())

    return context
