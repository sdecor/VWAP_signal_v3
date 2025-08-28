# signals/metrics/perf_tracker.py

from dataclasses import dataclass

@dataclass
class FuturesSpec:
    tick_size: float
    tick_value: float

class PerformanceTracker:
    """
    Suivi P&L temps réel (réalisé / latent), equity et drawdown.
    Hypothèse : positions linéaires (long/short) sur futures, prix en même unité
    que tes CSV. P&L = (delta_price / tick_size) * tick_value * qty * side.
    side: +1 long, -1 short.
    """

    def __init__(self, spec: FuturesSpec):
        self.spec = spec
        self.position_qty = 0.0     # >0 long, <0 short
        self.entry_price = None     # prix moyen d'entrée de la position
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.equity = 0.0
        self.max_equity = 0.0
        self.drawdown = 0.0
        self.n_trades = 0
        self.last_price = None

    def _pnl_between(self, price_a: float, price_b: float, qty: float) -> float:
        ticks = (price_b - price_a) / self.spec.tick_size
        return ticks * self.spec.tick_value * qty

    def on_fill(self, *, price: float, qty: float, side: str):
        """
        Enregistre un fill d'ordre (ou ouverture/augmentation).
        side: "BUY" (qty positive) ou "SELL" (qty positive).
        """
        side_mult = 1 if side.upper() == "BUY" else -1
        fill_qty = qty * side_mult

        # Si la position change de signe, on réalise le P&L sur la partie qui se ferme.
        if self.position_qty == 0:
            # Ouverture
            self.position_qty = fill_qty
            self.entry_price = price
            self.n_trades += 1
        elif (self.position_qty > 0 and fill_qty < 0) or (self.position_qty < 0 and fill_qty > 0):
            # Réduction / inversion
            remaining = self.position_qty + fill_qty
            if remaining == 0:
                # fermeture complète
                self.realized_pnl += self._pnl_between(self.entry_price, price, self.position_qty)
                self.position_qty = 0.0
                self.entry_price = None
                self.n_trades += 1
            elif (self.position_qty > 0 and remaining > 0) or (self.position_qty < 0 and remaining < 0):
                # réduction partielle
                closed_qty = self.position_qty - remaining
                self.realized_pnl += self._pnl_between(self.entry_price, price, closed_qty)
                self.position_qty = remaining
                # entry_price reste identique (même coût pour le restant)
                self.n_trades += 1
            else:
                # inversion de position: ferme l'ancienne + ouvre nouvelle partie
                self.realized_pnl += self._pnl_between(self.entry_price, price, self.position_qty)
                self.position_qty = remaining
                self.entry_price = price  # nouvelle base de coût pour la partie inversée
                self.n_trades += 1
        else:
            # Augmentation dans le même sens -> recalcul prix moyen d'entrée
            total_qty = self.position_qty + fill_qty
            if total_qty != 0:
                weighted_cost = (self.entry_price * abs(self.position_qty) + price * abs(fill_qty)) / abs(total_qty)
                self.entry_price = weighted_cost
            self.position_qty = total_qty
            self.n_trades += 1

        self.last_price = price
        self._mark_to_market(price)

    def on_mark(self, *, price: float):
        """Appelé à chaque nouveau prix pour MAJ l'Unrealized PnL et l'equity."""
        self.last_price = price
        self._mark_to_market(price)

    def _mark_to_market(self, price: float):
        if self.position_qty and self.entry_price is not None:
            self.unrealized_pnl = self._pnl_between(self.entry_price, price, self.position_qty)
        else:
            self.unrealized_pnl = 0.0

        self.equity = self.realized_pnl + self.unrealized_pnl
        if self.equity > self.max_equity:
            self.max_equity = self.equity
        dd = self.max_equity - self.equity
        self.drawdown = dd if dd > 0 else 0.0

    def snapshot(self):
        return {
            "equity": self.equity,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "drawdown": self.drawdown,
            "max_equity": self.max_equity,
            "n_trades": self.n_trades,
            "position_size": self.position_qty,
            "last_price": self.last_price,
        }
