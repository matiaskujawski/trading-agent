"""Prueba de punta a punta del contrato de decisión (sin gastar tokens todavía):
busca el primer gatillo técnico en el historial, arma el resumen de mercado,
y muestra qué decisión "de mentira" (mock) produce el pipeline completo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.backtest.strategy_baseline import moving_average_crossover
from src.llm_decision.market_summary import build_market_summary
from src.llm_decision.mock_decision import mock_decision

TRIGGER_REASONS = {
    "buy": "cruce_alcista_medias_moviles",
    "sell": "cruce_bajista_medias_moviles",
}

if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/binance_BTC-USDT_1d.csv"
    symbol = Path(csv_path).stem
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])

    for i in range(51, len(df)):
        window = df.iloc[: i + 1]
        signal = moving_average_crossover(window)
        if signal in TRIGGER_REASONS:
            risk_state = {
                "daily_loss_used_pct": 0.0,
                "distance_to_max_drawdown_pct": 1.0,
                "max_position_size_usd": 25.0,
            }
            summary = build_market_summary(window, symbol, TRIGGER_REASONS[signal], risk_state)
            decision = mock_decision(summary)

            print("Primer gatillo encontrado:")
            print(summary)
            print("\nDecisión (mock):")
            print(decision)
            break
    else:
        print("No se encontró ningún gatillo en el historial.")
