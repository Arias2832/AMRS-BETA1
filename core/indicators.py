"""
Módulo para cálculo de indicadores técnicos
AMRS BETA1 - Mean Reversion Strategy
"""

import pandas as pd
import pandas_ta as ta
import numpy as np


class IndicatorCalculator:
    """Calculador de indicadores técnicos para la estrategia"""

    def __init__(self, ema_period=20, atr_period=14, adx_period=14, rsi_period=14, atr_adjustment=1.0):
        """
        Inicializa el calculador con períodos de indicadores

        Args:
            ema_period: Período de EMA (default: 20)
            atr_period: Período de ATR (default: 14)
            adx_period: Período de ADX (default: 14)
            rsi_period: Período de RSI (default: 14)
            atr_adjustment: Factor de ajuste ATR para calibrar con MT5 (default: 1.0)
        """
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.adx_period = adx_period
        self.rsi_period = rsi_period
        self.atr_adjustment = atr_adjustment

    def calculate_ema(self, df):
        """
        Calcula Exponential Moving Average

        Args:
            df: DataFrame con columna 'close'

        Returns:
            pd.DataFrame: DataFrame con columna 'ema20' añadida
        """
        df['ema20'] = ta.ema(df['close'], length=self.ema_period)
        return df

    def calculate_atr(self, df):
        """
        Calcula Average True Range usando método Wilder (mismo que MT5)

        El método Wilder usa RMA (Running Moving Average) también conocido como
        Smoothed Moving Average, que es el método estándar en MT5.

        Args:
            df: DataFrame con columnas 'high', 'low', 'close'

        Returns:
            pd.DataFrame: DataFrame con columna 'atr' añadida
        """
        print(f"   📊 Calculando ATR con método Wilder (período {self.atr_period})...")
        print(f"      🔧 Factor de ajuste configurado: {self.atr_adjustment}")

        # Calcular True Range
        tr1 = df['high'] - df['low']  # High - Low
        tr2 = abs(df['high'] - df['close'].shift())  # |High - Previous Close|
        tr3 = abs(df['low'] - df['close'].shift())  # |Low - Previous Close|

        # True Range es el máximo de los tres
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR usando método Wilder (RMA/Smoothed MA)
        atr = tr.ewm(alpha=1 / self.atr_period, min_periods=self.atr_period, adjust=False).mean()

        # Debug: ATR antes del ajuste
        debug_date = pd.Timestamp('2025-08-06 16:00:00')
        if debug_date in df['datetime'].values:
            atr_before = atr[df['datetime'] == debug_date].iloc[0]
            print(f"      🔍 ATR ANTES del ajuste en {debug_date}: {atr_before:.5f}")

        # Aplicar factor de ajuste
        print(f"      ⚙️  Aplicando factor de ajuste ATR: {self.atr_adjustment}")
        atr = atr * self.atr_adjustment

        # Debug: ATR después del ajuste
        if debug_date in df['datetime'].values:
            atr_after = atr[df['datetime'] == debug_date].iloc[0]
            print(f"      🔍 ATR DESPUÉS del ajuste en {debug_date}: {atr_after:.5f}")

        df['atr'] = atr

        return df

    def calculate_atr_bands(self, df):
        """
        Calcula bandas ATR alrededor de EMA20

        Bandas:
        - ATR±2.0: Banda de referencia
        - ATR±2.2: Nivel de entrada (usada en estrategia)
        - ATR±3.0: Nivel de stop loss

        Args:
            df: DataFrame con columnas 'ema20' y 'atr'

        Returns:
            pd.DataFrame: DataFrame con bandas ATR añadidas
        """
        # Bandas superiores (para operaciones SHORT)
        df['atr_upper_2'] = df['ema20'] + (df['atr'] * 2.0)
        df['atr_upper_2_2'] = df['ema20'] + (df['atr'] * 2.2)
        df['atr_upper_3'] = df['ema20'] + (df['atr'] * 3.0)

        # Bandas inferiores (para operaciones LONG)
        df['atr_lower_2'] = df['ema20'] - (df['atr'] * 2.0)
        df['atr_lower_2_2'] = df['ema20'] - (df['atr'] * 2.2)
        df['atr_lower_3'] = df['ema20'] - (df['atr'] * 3.0)

        return df

    def calculate_adx(self, df):
        """
        Calcula ADX (Average Directional Index) y Directional Indicators

        Args:
            df: DataFrame con columnas 'high', 'low', 'close'

        Returns:
            pd.DataFrame: DataFrame con 'adx', 'plus_di', 'minus_di' añadidos
        """
        # pandas_ta calcula ADX con +DI y -DI
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=self.adx_period)

        # Añadir columnas al dataframe
        df['adx'] = adx_df[f'ADX_{self.adx_period}']
        df['plus_di'] = adx_df[f'DMP_{self.adx_period}']
        df['minus_di'] = adx_df[f'DMN_{self.adx_period}']

        return df

    def calculate_rsi(self, df):
        """
        Calcula Relative Strength Index

        Args:
            df: DataFrame con columna 'close'

        Returns:
            pd.DataFrame: DataFrame con columna 'rsi' añadida
        """
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)
        return df

    def calculate_all_indicators(self, df):
        """
        Calcula todos los indicadores necesarios para la estrategia

        Args:
            df: DataFrame con datos OHLCV

        Returns:
            pd.DataFrame: DataFrame con todos los indicadores calculados
        """
        print("\n🔢 Calculando indicadores...")

        # Hacer copia para no modificar original
        df = df.copy()

        # Calcular indicadores en orden
        print("   📊 Calculando EMA20...")
        df = self.calculate_ema(df)

        print("   📊 Calculando ATR(14)...")
        df = self.calculate_atr(df)

        print("   📊 Calculando bandas ATR...")
        df = self.calculate_atr_bands(df)

        print("   📊 Calculando ADX y Directional Indicators...")
        df = self.calculate_adx(df)

        print("   📊 Calculando RSI...")
        df = self.calculate_rsi(df)

        # Eliminar filas con NaN (warm-up period de indicadores)
        initial_rows = len(df)
        df = df.dropna()
        removed_rows = initial_rows - len(df)

        print(f"\n✅ Indicadores calculados exitosamente")
        print(f"   Filas removidas (warm-up): {removed_rows}")
        print(f"   Filas válidas: {len(df)}")
        print(f"   Primera vela válida: {df['datetime'].iloc[0]}")

        return df

    def get_indicator_summary(self, df):
        """
        Muestra resumen estadístico de los indicadores

        Args:
            df: DataFrame con indicadores calculados
        """
        print("\n" + "=" * 60)
        print("RESUMEN DE INDICADORES")
        print("=" * 60)

        indicators = {
            'EMA20': 'ema20',
            'ATR': 'atr',
            'ADX': 'adx',
            '+DI': 'plus_di',
            '-DI': 'minus_di',
            'RSI': 'rsi'
        }

        for name, col in indicators.items():
            if col in df.columns:
                print(f"\n{name}:")
                print(f"   Min: {df[col].min():.5f}")
                print(f"   Max: {df[col].max():.5f}")
                print(f"   Media: {df[col].mean():.5f}")
                print(f"   Último valor: {df[col].iloc[-1]:.5f}")