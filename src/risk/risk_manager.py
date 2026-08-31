"""Capa de riesgo determinística: nunca delegada al criterio del LLM (ver CONTEXTO.md)."""


class RiskManager:
    def __init__(self, starting_capital, max_drawdown, daily_loss_limit, stop_loss_per_trade=None):
        self.starting_capital = starting_capital
        self.max_drawdown = max_drawdown
        self.daily_loss_limit = daily_loss_limit
        self.stop_loss_per_trade = stop_loss_per_trade

        self.peak_equity = starting_capital
        self.daily_loss = 0.0
        self.current_day = None
        self.halted = False

    def roll_day(self, day):
        if day != self.current_day:
            self.current_day = day
            self.daily_loss = 0.0

    def update_peak(self, candidate_equity):
        self.peak_equity = max(self.peak_equity, candidate_equity)

    def check_drawdown_breach(self, worst_case_equity) -> bool:
        """Devuelve True solo la primera vez que se detecta la ruptura (evento nuevo)."""
        if self.halted:
            return False
        drawdown = self.peak_equity - worst_case_equity
        if drawdown >= self.max_drawdown:
            self.halted = True
            return True
        return False

    def register_trade_pnl(self, pnl, day):
        self.roll_day(day)
        if pnl < 0:
            self.daily_loss += -pnl

    def can_trade(self):
        if self.halted:
            return False, "drawdown_maximo_alcanzado"
        if self.daily_loss >= self.daily_loss_limit:
            return False, "limite_perdida_diaria_alcanzado"
        return True, None
