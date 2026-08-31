"""Tamaño de posición basado en riesgo: nunca arriesgar más que el stop-loss por
operación definido, sin importar cuánto capital total haya disponible."""


def position_size(capital: float, stop_loss_dollar: float, entry_price: float, stop_distance_pct: float) -> float:
    """
    Cantidad (unidades del activo) tal que, si el precio se mueve stop_distance_pct
    en contra desde entry_price, la pérdida sea aprox. stop_loss_dollar (antes de
    fees/slippage). Nunca devuelve una posición que cueste más que el capital disponible.
    """
    stop_distance = entry_price * stop_distance_pct
    if stop_distance <= 0:
        return 0.0
    qty_by_risk = stop_loss_dollar / stop_distance
    qty_by_capital = capital / entry_price
    return min(qty_by_risk, qty_by_capital)
