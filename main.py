"""
Script principal: Descarga + Indicadores + Detección de Setups
AMRS BETA1 - Mean Reversion Strategy
"""

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
            start_date=config.START_DATE,
            end_date=config.END_DATE
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
        atr_adjustment=config.ATR_ADJUSTMENT_FACTOR
    )

    df_with_indicators = calculator.calculate_all_indicators(df)
    calculator.get_indicator_summary(df_with_indicators)

    return df_with_indicators


def detect_setups(df, start_date, end_date):
    """Detecta setups de trading en el período especificado"""
    print("\n" + "=" * 70)
    print("PASO 3: DETECCIÓN DE SETUPS")
    print("=" * 70)

    detector = SetupDetector(min_candles_away=0)

    # Detectar setups
    setups = detector.detect_all_setups(
        df,
        start_date=start_date,
        end_date=end_date
    )

    # Imprimir setups
    detector.print_setups()

    # Exportar a CSV
    if setups:
        export_file = f"results/setups_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        detector.export_to_csv(export_file)

    return setups


def save_processed_data(df):
    """Guarda DataFrame con indicadores calculados"""
    processed_file = config.HISTORICAL_DATA_FILE.replace('.csv', '_processed.csv')
    df.to_csv(processed_file, index=False)
    print(f"\n💾 Datos procesados guardados en: {processed_file}")


def main():
    """Pipeline completo: Descarga + Indicadores + Detección"""
    import os

    # FORZAR RECÁLCULO: Borrar archivos procesados
    # (necesario cuando se cambia factor ATR o parámetros de indicadores)
    processed_file = config.HISTORICAL_DATA_FILE.replace('.csv', '_processed.csv')
    if os.path.exists(processed_file):
        print(f"\n🗑️  Borrando archivo procesado anterior para recalcular con nuevos parámetros...")
        print(f"   Archivo: {processed_file}")
        os.remove(processed_file)
        print(f"   ✅ Borrado exitoso")

    # PASO 1: Obtener datos (descargar o cargar existentes)
    if os.path.exists(config.HISTORICAL_DATA_FILE):
        print("\n📂 Datos históricos ya existen.")
        print(f"   Archivo: {config.HISTORICAL_DATA_FILE}")

        response = input("\n¿Quieres re-descargar datos? (s/n): ").lower()

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

    # PASO 3: Detectar setups en período específico
    # Agosto 1 - Septiembre 29, 2025
    start_date = datetime(2025, 3, 1)
    end_date = datetime(2025, 10, 17)

    # DEBUG: Verificar bandas ATR en fecha específica de entrada
    print("\n" + "=" * 70)
    print("🔍 DEBUG: Verificando cálculo de bandas ATR")
    print("=" * 70)

    # Fecha de entrada del SETUP #1: 2025-08-06 16:00:00
    debug_date = datetime(2025, 8, 6, 16, 0, 0)
    debug_row = df_processed[df_processed['datetime'] == debug_date]

    if not debug_row.empty:
        row = debug_row.iloc[0]
        print(f"\n📅 Fecha: {debug_date}")
        print(f"💰 Close: {row['close']:.5f}")
        print(f"📊 EMA20: {row['ema20']:.5f}")
        print(f"📊 ATR: {row['atr']:.5f}")
        print(f"\n🔴 Bandas superiores (SHORT):")
        print(f"   ATR+2.0: {row['atr_upper_2']:.5f}")
        print(f"   ATR+2.2: {row['atr_upper_2_2']:.5f} ← ENTRADA")
        print(f"   ATR+3.0: {row['atr_upper_3']:.5f} ← STOP LOSS")
        print(f"\n🟢 Bandas inferiores (LONG):")
        print(f"   ATR-2.0: {row['atr_lower_2']:.5f}")
        print(f"   ATR-2.2: {row['atr_lower_2_2']:.5f} ← ENTRADA")
        print(f"   ATR-3.0: {row['atr_lower_3']:.5f} ← STOP LOSS")

        print(f"\n📍 VALORES ESPERADOS DE MT5:")
        print(f"   ATR+2.0: 1.16434 (según gráfico)")
        print(f"   ATR+3.0: 1.16857 (según gráfico)")

        # Calcular manualmente para verificar
        manual_atr_upper_2 = row['ema20'] + (row['atr'] * 2.0)
        manual_atr_upper_22 = row['ema20'] + (row['atr'] * 2.2)
        manual_atr_upper_3 = row['ema20'] + (row['atr'] * 3.0)

        print(f"\n🔧 CÁLCULO MANUAL:")
        print(f"   EMA20 + (ATR × 2.0) = {row['ema20']:.5f} + ({row['atr']:.5f} × 2.0) = {manual_atr_upper_2:.5f}")
        print(f"   EMA20 + (ATR × 2.2) = {row['ema20']:.5f} + ({row['atr']:.5f} × 2.2) = {manual_atr_upper_22:.5f}")
        print(f"   EMA20 + (ATR × 3.0) = {row['ema20']:.5f} + ({row['atr']:.5f} × 3.0) = {manual_atr_upper_3:.5f}")

    setups = detect_setups(df_processed, start_date, end_date)

    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETADO EXITOSAMENTE")
    print("=" * 70)
    print(f"\n📊 Total de setups encontrados: {len(setups)}")
    print(f"📅 Período analizado: {start_date.date()} a {end_date.date()}")

    if setups:
        print(f"\n💡 Próximo paso:")
        print(f"   Compara estos {len(setups)} setups con tus trades manuales")
        print(f"   Revisa el archivo CSV en results/ para análisis detallado")


if __name__ == "__main__":
    # Crear carpetas si no existen
    import os

    os.makedirs('results', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    main()