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
        """
        Inicializa conexión con MT5

        Args:
            login: Número de cuenta (None = cuenta por defecto)
            password: Contraseña de cuenta
            server: Servidor del broker

        Returns:
            bool: True si conexión exitosa
        """
        if not mt5.initialize():
            print(f"❌ Error al inicializar MT5: {mt5.last_error()}")
            return False

        # Login si se proporcionan credenciales
        if login is not None:
            if not mt5.login(login, password, server):
                print(f"❌ Error al hacer login: {mt5.last_error()}")
                mt5.shutdown()
                return False

        self.connected = True

        # Información de la conexión
        account_info = mt5.account_info()
        if account_info:
            print(f"✅ Conectado a MT5")
            print(f"   Cuenta: {account_info.login}")
            print(f"   Servidor: {account_info.server}")
            print(f"   Balance: ${account_info.balance:.2f}")

        return True

    def download_historical_data(self, symbol, timeframe, start_date, end_date):
        """
        Descarga datos históricos desde MT5

        Args:
            symbol: Par de divisas (ej: "EURUSD")
            timeframe: Timeframe MT5 (ej: mt5.TIMEFRAME_H4)
            start_date: Fecha inicial (datetime)
            end_date: Fecha final (datetime)

        Returns:
            pd.DataFrame: DataFrame con datos OHLCV
        """
        if not self.connected:
            print("❌ No hay conexión con MT5. Ejecuta initialize() primero.")
            return None

        print(f"\n📊 Descargando datos históricos...")
        print(f"   Símbolo: {symbol}")
        print(f"   Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")

        # Solicitar datos
        rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)

        if rates is None or len(rates) == 0:
            print(f"❌ Error al descargar datos: {mt5.last_error()}")
            return None

        # Convertir a DataFrame
        df = pd.DataFrame(rates)

        # Convertir timestamp a datetime
        df['time'] = pd.to_datetime(df['time'], unit='s')

        # Renombrar columnas para claridad
        df.rename(columns={
            'time': 'datetime',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'tick_volume': 'volume'
        }, inplace=True)

        # Seleccionar solo columnas relevantes
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]

        print(f"✅ Datos descargados exitosamente")
        print(f"   Total de velas: {len(df)}")
        print(f"   Primera vela: {df['datetime'].iloc[0]}")
        print(f"   Última vela: {df['datetime'].iloc[-1]}")

        # Validar datos
        self._validate_data(df)

        return df

    def _validate_data(self, df):
        """
        Valida integridad de los datos descargados

        Args:
            df: DataFrame con datos históricos
        """
        print(f"\n🔍 Validando datos...")

        # Verificar valores nulos
        null_counts = df.isnull().sum()
        if null_counts.sum() > 0:
            print(f"⚠️  Advertencia: Se encontraron valores nulos:")
            print(null_counts[null_counts > 0])
        else:
            print(f"✅ Sin valores nulos")

        # Verificar duplicados de tiempo
        duplicates = df['datetime'].duplicated().sum()
        if duplicates > 0:
            print(f"⚠️  Advertencia: {duplicates} timestamps duplicados")
        else:
            print(f"✅ Sin timestamps duplicados")

        # Verificar orden cronológico
        if not df['datetime'].is_monotonic_increasing:
            print(f"⚠️  Advertencia: Datos no están en orden cronológico")
        else:
            print(f"✅ Datos en orden cronológico")

        # Estadísticas básicas
        print(f"\n📈 Estadísticas:")
        print(f"   Precio mínimo: {df['low'].min():.5f}")
        print(f"   Precio máximo: {df['high'].max():.5f}")
        print(f"   Precio promedio: {df['close'].mean():.5f}")

    def save_to_csv(self, df, filepath):
        """
        Guarda DataFrame a archivo CSV

        Args:
            df: DataFrame con datos
            filepath: Ruta del archivo
        """
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Guardar
        df.to_csv(filepath, index=False)
        print(f"\n💾 Datos guardados en: {filepath}")
        print(f"   Tamaño del archivo: {os.path.getsize(filepath) / 1024:.2f} KB")

    def shutdown(self):
        """Cierra conexión con MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print(f"\n🔌 Desconectado de MT5")