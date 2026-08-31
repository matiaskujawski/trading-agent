"""Límite de correlación entre activos abiertos simultáneamente (Opción A: se
recalcula solo, con una ventana móvil -- no son grupos fijos definidos a mano).
Evita que varias posiciones abiertas sean, en la práctica, la misma apuesta
repetida varias veces."""

import pandas as pd


def max_correlation_with_open(
    candidate_returns: pd.Series, open_returns: dict[str, pd.Series]
) -> tuple[float, str | None]:
    """Correlación POSITIVA más alta entre el candidato y cualquier posición ya
    abierta (nunca negativa: dos posiciones que se mueven en direcciones
    opuestas son una cobertura natural, no una concentración oculta -- no hay
    que bloquearlas). (0.0, None) si no hay nada abierto."""
    best_corr, best_symbol = 0.0, None

    for symbol, returns in open_returns.items():
        aligned = pd.concat([candidate_returns, returns], axis=1, join="inner").dropna()
        if len(aligned) < 10:
            continue
        corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
        if pd.notna(corr) and corr > best_corr:
            best_corr, best_symbol = corr, symbol

    return best_corr, best_symbol


def passes_correlation_limit(
    candidate_returns: pd.Series, open_returns: dict[str, pd.Series], threshold: float = 0.5
) -> tuple[bool, float, str | None]:
    corr, symbol = max_correlation_with_open(candidate_returns, open_returns)
    return corr <= threshold, corr, symbol
