"""
Módulo para conexión con MetaTrader5 y descarga de datos históricos
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import os


class MT5Connector:
    """Manejador de conexión y descarga de datos desde MT5"""

    def __init__(self):
        self.connected = False

    def initialize(self, login=None, password="", server=""):
        """Inicializa conexión con MT5"""
        if not mt5.initialize():
            print(f"❌ Error al inicializar MT5: {mt5.last_error()}")
            return False

        if login is not None:
            if not mt5.login(login, password, server):
                print(f"❌ Error al hacer login: {mt5.last_error()}")
                mt5.shutdown()
                return False

        self.connected = True
        account_info = mt5.account_info()
        if account_info:
            print(f"✅ Conectado a MT5 - Cuenta: {account_info.login} | Servidor: {account_info.server}")

        return True

    def download_historical_data(self, symbol, timeframe, start_date, end_date):
        """Descarga datos históricos desde MT5"""
        if not self.connected:
            print("❌ No hay conexión con MT5")
            return None

        print(f"📊 Descargando {symbol} desde {start_date.strftime('%Y-%m-%d')} hasta {end_date.strftime('%Y-%m-%d')}")

        rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)

        if rates is None or len(rates) == 0:
            print(f"❌ Error al descargar datos: {mt5.last_error()}")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.rename(columns={
            'time': 'datetime',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'tick_volume': 'volume'
        }, inplace=True)

        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]

        print(f"✅ {len(df)} velas descargadas ({df['datetime'].iloc[0]} - {df['datetime'].iloc[-1]})")
        self._validate_data(df)
        return df

    def _validate_data(self, df):
        """Valida integridad de los datos descargados"""
        null_counts = df.isnull().sum()
        duplicates = df['datetime'].duplicated().sum()
        chronological = df['datetime'].is_monotonic_increasing

        issues = []
        if null_counts.sum() > 0:
            issues.append(f"{null_counts.sum()} valores nulos")
        if duplicates > 0:
            issues.append(f"{duplicates} timestamps duplicados")
        if not chronological:
            issues.append("datos fuera de orden")

        if issues:
            print(f"⚠️  Advertencias: {', '.join(issues)}")

    def save_to_csv(self, df, filepath):
        """Guarda DataFrame a archivo CSV"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df.to_csv(filepath, index=False)
        print(f"💾 Datos guardados: {filepath} ({os.path.getsize(filepath) / 1024:.1f} KB)")

    def shutdown(self):
        """Cierra conexión con MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("🔌 Desconectado de MT5")