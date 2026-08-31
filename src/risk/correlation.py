"""Límite de correlación entre activos abiertos simultáneamente (Opción A: se
recalcula solo, con una ventana móvil -- no son grupos fijos definidos a mano).
Evita que varias posiciones abiertas sean, en la práctica, la misma apuesta
repetida varias veces."""

import pandas as pd


def max_correlation_with_open(
    candidate_returns: pd.Series, open_returns: dict[str, pd.Series]
) -> tuple[float, str | None]:
    """Correlación más alta entre el candidato y cualquier posición ya abierta,
    junto con qué activo la produjo. (0.0, None) si no hay nada abierto."""
    best_corr, best_symbol = 0.0, None

    for symbol, returns in open_returns.items():
        aligned = pd.concat([candidate_returns, returns], axis=1, join="inner").dropna()
        if len(aligned) < 10:
            continue
        corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
        if pd.notna(corr) and abs(corr) > abs(best_corr):
            best_corr, best_symbol = corr, symbol

    return best_corr, best_symbol


def passes_correlation_limit(
    candidate_returns: pd.Series, open_returns: dict[str, pd.Series], threshold: float = 0.7
) -> tuple[bool, float, str | None]:
    corr, symbol = max_correlation_with_open(candidate_returns, open_returns)
    return abs(corr) <= threshold, corr, symbol
