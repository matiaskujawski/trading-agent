# Universo de activos aprobado (ver CONTEXTO.md): solo cripto de valor / proyectos
# importantes y pares forex mayores. Nada de shitcoins ni exóticos.
CRYPTO_SYMBOLS = ["BTC/USDT", "ETH/USDT", "LINK/USDT", "UNI/USDT", "CAKE/USDT", "XRP/USDT"]
FOREX_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD"]

# Parámetros de riesgo (ver CONTEXTO.md). Nunca se cambian en código sin
# confirmación explícita del usuario en el chat.
RISK_PARAMS = {
    "starting_capital": 10_000,
    "max_drawdown": 2_000,
    "daily_loss_limit": 200,
    "stop_loss_per_trade": 25,  # confirmado explícitamente por el usuario el 2026-08-30
}
