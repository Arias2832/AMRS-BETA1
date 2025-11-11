"""
Script principal: Descarga + Indicadores + Detección de Setups
AMRS BETA1 - Mean Reversion Strategy
"""
import MetaTrader5 as mt5
import sys
sys.path.append('.')

import pandas as pd
from datetime import datetime
from core.mt5_connector import MT5Connector
from core.indicators import IndicatorCalculator
from core.setup_detector import SetupDetector
from config import config


def download_data():
    """Descarga datos históricos de MT5"""
    print("=" * 70)
    print("PASO 1: DESCARGA DE DATOS HISTÓRICOS")
    print("=" * 70)

    connector = MT5Connector()

    try:
        if not connector.initialize(
                login=config.MT5_LOGIN,
                password=config.MT5_PASSWORD,
                server=config.MT5_SERVER
        ):
            print("\n❌ No se pudo conectar a MT5")
            return None

        df = connector.download_historical_data(
            symbol=config.SYMBOL,
            timeframe=config.TIMEFRAME,
            start_date=config.DATA_START_DATE,
            end_date=config.DATA_END_DATE
        )

        if df is None:
            return None

        connector.save_to_csv(df, config.HISTORICAL_DATA_FILE)
        return df

    finally:
        connector.shutdown()


def calculate_indicators(df):
    """Calcula todos los indicadores técnicos"""
    print("\n" + "=" * 70)
    print("PASO 2: CÁLCULO DE INDICADORES")
    print("=" * 70)

    calculator = IndicatorCalculator(
        ema_period=config.EMA_PERIOD,
        atr_period=config.ATR_PERIOD,
        adx_period=config.ADX_PERIOD,
        rsi_period=config.RSI_PERIOD,
        atr_adjustment=config.ATR_ADJUSTMENT_FACTOR,
        atr_entry_multiplier=config.ATR_ENTRY_MULTIPLIER
    )

    df_with_indicators = calculator.calculate_all_indicators(df)
    calculator.get_indicator_summary(df_with_indicators)

    return df_with_indicators


def detect_setups(df, start_date, end_date):
    """Detecta setups de trading en el período especificado"""
    print("\n" + "=" * 70)
    print("PASO 3: DETECCIÓN DE SETUPS")
    print("=" * 70)

    detector = SetupDetector(
        symbol=config.SYMBOL,  # ← AGREGAR ESTA LÍNEA
        min_candles_away=0,
        use_di_filter=config.USE_DI_SPREAD_FILTER,
        di_spread_max=config.DI_SPREAD_MAX
    )

    # Mostrar configuración de filtros si están activos
    if config.USE_DI_SPREAD_FILTER:
        print(f"🔧 Filtro DI activado: |+DI - -DI| < {config.DI_SPREAD_MAX}")

    setups = detector.detect_all_setups(
        df,
        start_date=start_date,
        end_date=end_date
    )

    detector.print_setups()
    # Obtener nombre de timeframe
    timeframe_map = {
        mt5.TIMEFRAME_H1: "H1",
        mt5.TIMEFRAME_H4: "H4",
        mt5.TIMEFRAME_H6: "H6",
        mt5.TIMEFRAME_M30: "M30",
        mt5.TIMEFRAME_D1: "D1"
    }
    timeframe_name = timeframe_map.get(config.TIMEFRAME, "H4")
    # Exportar a CSV
    if setups:
        export_file = f"results/setups_{config.SYMBOL}_{timeframe_name}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        detector.export_to_csv(export_file)

    # Generar resumen ejecutivo
    detector.get_executive_summary(config.SYMBOL, start_date, end_date)

    return setups


def save_processed_data(df):
    """Guarda DataFrame con indicadores calculados"""
    processed_file = config.HISTORICAL_DATA_FILE.replace('.csv', '_processed.csv')
    df.to_csv(processed_file, index=False)
    print(f"\n💾 Datos procesados guardados: {processed_file}")


def main():
    """Pipeline completo: Descarga + Indicadores + Detección"""
    import os

    # Forzar recálculo: Borrar archivos procesados
    processed_file = config.HISTORICAL_DATA_FILE.replace('.csv', '_processed.csv')
    if os.path.exists(processed_file):
        print(f"\n🗑️ Borrando archivo procesado anterior para recalcular...")
        os.remove(processed_file)

    # PASO 1: Obtener datos
    if os.path.exists(config.HISTORICAL_DATA_FILE):
        print(f"\n📂 Datos históricos existentes: {config.HISTORICAL_DATA_FILE}")
        response = input("\n¿Re-descargar datos? (s/n): ").lower()

        if response == 's':
            df = download_data()
            if df is None:
                return
        else:
            print("\n📊 Cargando datos existentes...")
            df = pd.read_csv(config.HISTORICAL_DATA_FILE)
            df['datetime'] = pd.to_datetime(df['datetime'])
            print(f"✅ {len(df)} velas cargadas")
    else:
        df = download_data()
        if df is None:
            return

    # PASO 2: Calcular indicadores
    df_processed = calculate_indicators(df)
    save_processed_data(df_processed)

    # PASO 3: Detectar setups
    setups = detect_setups(df_processed, config.ANALYSIS_START_DATE, config.ANALYSIS_END_DATE)

    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    import os
    os.makedirs('results', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    main()