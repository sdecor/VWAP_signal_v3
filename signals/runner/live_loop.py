# signals/runner/live_loop.py

import os
import time
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from signals.loaders.config_loader import get_live_data_path, validate_config
from signals.loaders.config_validator import validate_config_values
from signals.logic.trade_decider import decide_trade
from signals.logic.order_executor import execute_signal


class MarketDataHandler(FileSystemEventHandler):
    """
    Handler déclenché à chaque modification du fichier CSV 5m.
    Évite les doublons grâce à un léger debounce sur la mtime.
    """
    def __init__(self, watched_file: str, debounce_seconds: float = 0.5):
        self.watched_file = os.path.abspath(watched_file)
        self.debounce_seconds = debounce_seconds
        self._last_mtime: Optional[float] = None

    def _is_target(self, path: str) -> bool:
        return os.path.abspath(path) == self.watched_file

    def _debounced(self) -> bool:
        try:
            mtime = os.path.getmtime(self.watched_file)
        except FileNotFoundError:
            return False

        if self._last_mtime is None or (mtime - (self._last_mtime or 0)) > self.debounce_seconds:
            self._last_mtime = mtime
            return True
        return False

    def on_modified(self, event):
        if event.is_directory:
            return
        if not self._is_target(event.src_path):
            return
        if not self._debounced():
            return

        print(f"\n📈 Nouvelle barre détectée : {event.src_path}")
        try:
            signal = decide_trade()
            if signal:
                print(f"📤 Signal généré : {signal}")
                result = execute_signal(signal)
                print(f"📦 Résultat exécution: {result}")
            else:
                print("⏸️ Aucun signal à exécuter.")
        except Exception as e:
            print(f"❌ Erreur dans la prise de décision/exécution : {e}")


def run_live_loop():
    """
    Initialise l'observateur du fichier 5m et exécute la boucle temps réel.
    """
    validate_config_values()  # clés/valeurs/types
    validate_config()         # existence des fichiers

    watched_file = get_live_data_path()
    watch_dir = os.path.dirname(os.path.abspath(watched_file))

    print(f"👁️  Surveillance de : {watched_file}")
    print("📡 En attente de nouvelles barres... (Ctrl+C pour arrêter)")

    observer = Observer()
    event_handler = MarketDataHandler(watched_file)
    observer.schedule(event_handler, path=watch_dir, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé par l'utilisateur.")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    run_live_loop()
