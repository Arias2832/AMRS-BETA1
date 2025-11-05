"""
Módulo para cálculo de indicadores técnicos
AMRS BETA1 - Mean Reversion Strategy
"""

import pandas as pd
import pandas_ta as ta
import numpy as np


class IndicatorCalculator:
    """Calculador de indicadores técnicos para la estrategia"""

    def __init__(self, ema_period=20, atr_period=14, adx_period=14, rsi_period=14, atr_adjustment=1.0,
                 atr_entry_multiplier=2.2):
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.adx_period = adx_period
        self.rsi_period = rsi_period
        self.atr_adjustment = atr_adjustment
        self.atr_entry_multiplier = atr_entry_multiplier

    def calculate_ema(self, df):
        """Calcula Exponential Moving Average"""
        df['ema20'] = ta.ema(df['close'], length=self.ema_period)
        return df

    def calculate_atr(self, df):
        """Calcula Average True Range usando método Wilder"""
        # True Range
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR usando método Wilder (RMA/Smoothed MA)
        atr = tr.ewm(alpha=1 / self.atr_period, min_periods=self.atr_period, adjust=False).mean()
        atr = atr * self.atr_adjustment
        df['atr'] = atr
        return df

    def calculate_atr_bands(self, df):
        """Calcula bandas ATR alrededor de EMA20"""
        # Bandas superiores (para operaciones SHORT)
        df['atr_upper_2'] = df['ema20'] + (df['atr'] * 2.0)
        df['atr_upper_entry'] = df['ema20'] + (df['atr'] * self.atr_entry_multiplier)
        df['atr_upper_3'] = df['ema20'] + (df['atr'] * 3.0)

        # Bandas inferiores (para operaciones LONG)
        df['atr_lower_2'] = df['ema20'] - (df['atr'] * 2.0)
        df['atr_lower_entry'] = df['ema20'] - (df['atr'] * self.atr_entry_multiplier)
        df['atr_lower_3'] = df['ema20'] - (df['atr'] * 3.0)

        return df

    def calculate_adx(self, df):
        """Calcula ADX y Directional Indicators"""
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=self.adx_period)
        df['adx'] = adx_df[f'ADX_{self.adx_period}']
        df['plus_di'] = adx_df[f'DMP_{self.adx_period}']
        df['minus_di'] = adx_df[f'DMN_{self.adx_period}']
        return df

    def calculate_rsi(self, df):
        """Calcula Relative Strength Index"""
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)
        return df

    def calculate_all_indicators(self, df):
        """Calcula todos los indicadores necesarios para la estrategia"""
        print("\n📊 Calculando indicadores...")

        df = df.copy()
        df = self.calculate_ema(df)
        df = self.calculate_atr(df)
        df = self.calculate_atr_bands(df)
        df = self.calculate_adx(df)
        df = self.calculate_rsi(df)

        initial_rows = len(df)
        df = df.dropna()
        removed_rows = initial_rows - len(df)

        print(f"✅ Indicadores calculados: {len(df)} velas válidas ({removed_rows} removidas)")
        return df

    def get_indicator_summary(self, df):
        """Muestra resumen estadístico de los indicadores"""
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
                print(f"{name}: Min {df[col].min():.3f} | Max {df[col].max():.3f} | Último {df[col].iloc[-1]:.3f}")