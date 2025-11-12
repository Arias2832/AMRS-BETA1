"""
Optimizador de niveles ATR para estrategia Mean Reversion
Analiza diferentes niveles de entrada ATR y compara resultados

CONFIGURACIÓN:
- Cambiar SYMBOL y TIMEFRAME para diferentes pares
- Ajustar ATR_RANGE para probar más valores
- Modificar fechas de análisis según necesidad
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys

# Agregar paths para importar módulos del proyecto
sys.path.append('./core')
sys.path.append('./config')
sys.path.append('.')

# Importar módulos del proyecto
from core.indicators import IndicatorCalculator
from core.setup_detector import SetupDetector

# ============================================================================
# CONFIGURACIÓN DEL ANÁLISIS
# ============================================================================

# Par y temporalidad a analizar
SYMBOL = "EURUSD"
TIMEFRAME = "H4"

# Rango de niveles ATR a probar
ATR_RANGE = [1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8]

# Fechas para análisis de setups
ANALYSIS_START_DATE = datetime(2020, 3, 1)
ANALYSIS_END_DATE = datetime(2025, 10, 17)

# Parámetros base (mantener consistencia con config original)
BASE_PARAMS = {
    'ema_period': 20,
    'atr_period': 20,
    'adx_period': 14,
    'rsi_period': 14,
    'atr_adjustment': 0.99,
    'atr_stop_multiplier': 3.0,  # Stop loss fijo
    'min_candles_away': 0
}


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def find_processed_file(symbol, timeframe):
    """Busca automáticamente el archivo procesado en la carpeta Data/"""
    data_folder = "Data"

    if not os.path.exists(data_folder):
        raise FileNotFoundError(f"❌ Carpeta {data_folder}/ no encontrada")

    # Patrones posibles de archivo
    patterns = [
        f"{symbol}_{timeframe}_*_processed.csv",
        f"{symbol}_*_processed.csv",
        "*_processed.csv"
    ]

    files = os.listdir(data_folder)
    processed_files = [f for f in files if f.endswith('_processed.csv')]

    if not processed_files:
        raise FileNotFoundError(f"❌ No se encontraron archivos *_processed.csv en {data_folder}/")

    # Preferir archivo que coincida con símbolo
    for file in processed_files:
        if symbol in file and timeframe in file:
            return os.path.join(data_folder, file)

    # Usar el primer archivo procesado encontrado
    selected_file = os.path.join(data_folder, processed_files[0])
    print(f"⚠️  Usando archivo: {selected_file}")
    return selected_file


def load_processed_data(symbol, timeframe):
    """Carga dataset procesado existente"""
    file_path = find_processed_file(symbol, timeframe)

    print(f"📊 Cargando datos procesados: {file_path}")

    try:
        df = pd.read_csv(file_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        print(f"✅ Datos cargados: {len(df)} velas")
        print(f"   Período: {df['datetime'].iloc[0]} - {df['datetime'].iloc[-1]}")
        return df

    except Exception as e:
        raise Exception(f"❌ Error cargando datos: {e}")


def recalculate_atr_bands(df, atr_entry_multiplier):
    """Recalcula solo las bandas ATR con nuevo multiplicador de entrada"""
    df_copy = df.copy()

    # Recalcular bandas de entrada con nuevo multiplicador
    df_copy['atr_upper_entry'] = df_copy['ema20'] + (df_copy['atr'] * atr_entry_multiplier)
    df_copy['atr_lower_entry'] = df_copy['ema20'] - (df_copy['atr'] * atr_entry_multiplier)

    # Las bandas de stop loss siguen siendo fijas en ATR 3.0
    df_copy['atr_upper_3'] = df_copy['ema20'] + (df_copy['atr'] * BASE_PARAMS['atr_stop_multiplier'])
    df_copy['atr_lower_3'] = df_copy['ema20'] - (df_copy['atr'] * BASE_PARAMS['atr_stop_multiplier'])

    return df_copy


def analyze_atr_level(df, atr_entry_multiplier, start_date, end_date):
    """Analiza un nivel específico de ATR y retorna métricas"""

    # Recalcular bandas ATR con nuevo multiplicador
    df_with_new_bands = recalculate_atr_bands(df, atr_entry_multiplier)

    # Crear detector de setups
    detector = SetupDetector(min_candles_away=BASE_PARAMS['min_candles_away'])

    # Detectar setups con nuevas bandas
    setups = detector.detect_all_setups(
        df_with_new_bands,
        start_date=start_date,
        end_date=end_date
    )

    # Calcular métricas
    if not setups:
        return {
            'atr_level': atr_entry_multiplier,
            'total_trades': 0,
            'win_trades': 0,
            'loss_trades': 0,
            'win_rate': 0,
            'avg_win_pips': 0,
            'avg_loss_pips': 0,
            'total_pips': 0,
            'expectancy': 0,
            'profit_factor': 0,
            'trades_per_year': 0,
            'max_drawdown': 0
        }

    # Separar trades por resultado
    closed_trades = [s for s in setups if s['outcome'] in ['WIN', 'LOSS']]
    wins = [s for s in setups if s['outcome'] == 'WIN']
    losses = [s for s in setups if s['outcome'] == 'LOSS']

    if not closed_trades:
        return {
            'atr_level': atr_entry_multiplier,
            'total_trades': len(setups),
            'win_trades': 0,
            'loss_trades': 0,
            'win_rate': 0,
            'avg_win_pips': 0,
            'avg_loss_pips': 0,
            'total_pips': 0,
            'expectancy': 0,
            'profit_factor': 0,
            'trades_per_year': 0,
            'max_drawdown': 0
        }

    # Calcular métricas
    total_trades = len(closed_trades)
    win_trades = len(wins)
    loss_trades = len(losses)
    win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0

    total_pips = sum(s['result_pips'] for s in closed_trades)
    win_pips_total = sum(s['result_pips'] for s in wins)
    loss_pips_total = sum(s['result_pips'] for s in losses)

    avg_win_pips = win_pips_total / win_trades if win_trades > 0 else 0
    avg_loss_pips = abs(loss_pips_total) / loss_trades if loss_trades > 0 else 0

    expectancy = total_pips / total_trades if total_trades > 0 else 0
    profit_factor = win_pips_total / abs(loss_pips_total) if loss_pips_total != 0 else float('inf')

    # Calcular trades por año
    years = (end_date - start_date).days / 365.25
    trades_per_year = total_trades / years if years > 0 else 0

    # Max drawdown (aproximado)
    max_drawdown = min(s['result_pips'] for s in losses) if losses else 0

    return {
        'atr_level': atr_entry_multiplier,
        'total_trades': total_trades,
        'win_trades': win_trades,
        'loss_trades': loss_trades,
        'win_rate': win_rate,
        'avg_win_pips': avg_win_pips,
        'avg_loss_pips': avg_loss_pips,
        'total_pips': total_pips,
        'expectancy': expectancy,
        'profit_factor': profit_factor,
        'trades_per_year': trades_per_year,
        'max_drawdown': max_drawdown
    }


def generate_summary_table(results):
    """Genera tabla resumen ordenada por expectancia"""

    # Convertir a DataFrame para fácil manipulación
    df_results = pd.DataFrame(results)

    # Ordenar por expectancia (descendente)
    df_results = df_results.sort_values('expectancy', ascending=False)
    df_results['ranking'] = range(1, len(df_results) + 1)

    return df_results


def print_results_table(df_results, symbol, timeframe):
    """Imprime tabla de resultados formateada"""

    print("\n" + "=" * 100)
    print(f"📊 ANÁLISIS OPTIMIZACIÓN ATR - {symbol} {timeframe}")
    print("=" * 100)

    print(
        f"{'Rank':<4} {'ATR':<5} {'Trades':<7} {'Win%':<6} {'AvgWin':<8} {'AvgLoss':<8} {'Expect':<8} {'PF':<6} {'T/año':<6} {'Status':<12}")
    print("-" * 100)

    for _, row in df_results.iterrows():
        # Determinar status
        if row['expectancy'] > 8 and row['profit_factor'] > 1.8:
            status = "✅ EXCELENTE"
        elif row['expectancy'] > 5 and row['profit_factor'] > 1.5:
            status = "🟡 BUENA"
        elif row['expectancy'] > 2 and row['profit_factor'] > 1.2:
            status = "⚠️ MARGINAL"
        else:
            status = "❌ MALA"

        print(f"{row['ranking']:<4.0f} "
              f"{row['atr_level']:<5.1f} "
              f"{row['total_trades']:<7.0f} "
              f"{row['win_rate']:<6.1f} "
              f"{row['avg_win_pips']:<8.1f} "
              f"{row['avg_loss_pips']:<8.1f} "
              f"{row['expectancy']:<8.2f} "
              f"{row['profit_factor']:<6.2f} "
              f"{row['trades_per_year']:<6.1f} "
              f"{status:<12}")

    # Resumen del mejor
    best = df_results.iloc[0]
    print("\n" + "🏆 MEJOR CONFIGURACIÓN:")
    print(f"   ATR Level: {best['atr_level']:.1f}")
    print(f"   Expectancia: {best['expectancy']:+.2f} pips/trade")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Profit Factor: {best['profit_factor']:.2f}")
    print(f"   Trades por año: {best['trades_per_year']:.0f}")

    # Comparar con baseline (si ATR 2.2 está en resultados)
    baseline = df_results[df_results['atr_level'] == 2.2]
    if not baseline.empty:
        baseline = baseline.iloc[0]
        improvement = ((best['expectancy'] - baseline['expectancy']) / abs(baseline['expectancy'])) * 100
        print(f"\n📈 MEJORA vs ATR 2.2 (baseline):")
        print(
            f"   Expectancia: {baseline['expectancy']:+.2f} → {best['expectancy']:+.2f} pips/trade ({improvement:+.1f}%)")
        print(
            f"   Win Rate: {baseline['win_rate']:.1f}% → {best['win_rate']:.1f}% ({best['win_rate'] - baseline['win_rate']:+.1f}pp)")


def save_results_to_csv(df_results, symbol, timeframe):
    """Guarda resultados a CSV para análisis posterior"""

    os.makedirs('results', exist_ok=True)
    filename = f"results/atr_optimization_{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    df_results.to_csv(filename, index=False)
    print(f"\n💾 Resultados guardados: {filename}")


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def optimize_atr_levels(symbol, timeframe, atr_range, start_date, end_date):
    """Función principal de optimización"""

    print("🚀 INICIANDO OPTIMIZACIÓN DE NIVELES ATR")
    print("=" * 60)
    print(f"📊 Símbolo: {symbol}")
    print(f"⏰ Temporalidad: {timeframe}")
    print(f"🔢 Niveles ATR: {atr_range}")
    print(f"📅 Período análisis: {start_date.date()} - {end_date.date()}")
    print(
        f"📈 Parámetros base: EMA{BASE_PARAMS['ema_period']}, ATR{BASE_PARAMS['atr_period']}, ADX{BASE_PARAMS['adx_period']}")

    try:
        # Cargar datos
        df = load_processed_data(symbol, timeframe)

        # Validar que tiene las columnas necesarias
        required_columns = ['datetime', 'ema20', 'atr', 'adx', 'plus_di', 'minus_di', 'rsi']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(f"❌ Faltan columnas en el dataset: {missing_columns}")

        # Ejecutar análisis para cada nivel ATR
        results = []

        print(f"\n🔄 Analizando {len(atr_range)} niveles ATR...")

        for i, atr_level in enumerate(atr_range, 1):
            print(f"   [{i:2d}/{len(atr_range)}] Analizando ATR {atr_level}...", end="")

            try:
                metrics = analyze_atr_level(df, atr_level, start_date, end_date)
                results.append(metrics)
                print(f" ✅ {metrics['total_trades']} trades, {metrics['expectancy']:+.2f} pips")

            except Exception as e:
                print(f" ❌ Error: {e}")
                continue

        if not results:
            print("❌ No se pudieron analizar niveles ATR")
            return None

        # Generar tabla de resultados
        df_results = generate_summary_table(results)

        # Mostrar resultados
        print_results_table(df_results, symbol, timeframe)

        # Guardar resultados
        save_results_to_csv(df_results, symbol, timeframe)

        print("\n✅ OPTIMIZACIÓN COMPLETADA")

        return df_results

    except Exception as e:
        print(f"\n❌ ERROR EN OPTIMIZACIÓN: {e}")
        return None


# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

def main():
    """Ejecuta optimización con configuración actual"""

    results = optimize_atr_levels(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        atr_range=ATR_RANGE,
        start_date=ANALYSIS_START_DATE,
        end_date=ANALYSIS_END_DATE
    )

    if results is not None:
        print("\n💡 PRÓXIMOS PASOS:")
        print("   1. Analizar tabla de resultados")
        print("   2. Actualizar config.py con mejor ATR level")
        print("   3. Aplicar filtros adicionales (DI, ADX) al mejor nivel")
        print("   4. Ejecutar en otros pares/timeframes")


if __name__ == "__main__":
    main()