"""
Script para agregar MACD al dataset procesado - VERSIÓN FINAL
Uso: python add_macd_final.py
"""

import pandas as pd
import pandas_ta as ta
import os


def add_macd_to_dataset():
    """
    Agrega MACD al dataset procesado existente
    Busca automáticamente el archivo _processed.csv en la carpeta Data/
    """

    # Buscar archivo procesado automáticamente
    data_folder = "Data"
    processed_files = [f for f in os.listdir(data_folder) if f.endswith('_processed.csv')]

    if not processed_files:
        print("❌ Error: No se encontró archivo *_processed.csv en Data/")
        print("   Ejecuta main.py primero para generar el dataset procesado")
        return None

    # Usar el primer archivo encontrado
    processed_file = os.path.join(data_folder, processed_files[0])
    print(f"📊 Cargando dataset procesado: {processed_file}")

    try:
        df = pd.read_csv(processed_file)
        df['datetime'] = pd.to_datetime(df['datetime'])
        print(f"✅ Dataset cargado: {len(df)} velas")
        print(f"   Rango: {df['datetime'].iloc[0]} - {df['datetime'].iloc[-1]}")

    except Exception as e:
        print(f"❌ Error cargando archivo: {e}")
        return None

    # Verificar que existe columna close
    if 'close' not in df.columns:
        print("❌ Error: No se encontró columna 'close' en el dataset")
        return None

    # Calcular MACD
    print("\n📈 Calculando MACD (12, 26, 9)...")

    try:
        # MACD estándar (12, 26, 9)
        macd_data = ta.macd(df['close'], fast=12, slow=26, signal=9)

        # Agregar columnas MACD
        df['macd'] = macd_data['MACD_12_26_9']
        df['macd_signal'] = macd_data['MACDs_12_26_9']
        df['macd_histogram'] = macd_data['MACDh_12_26_9']

    except Exception as e:
        print(f"❌ Error calculando MACD: {e}")
        return None

    # Verificar cálculo
    valid_macd = df['macd'].dropna()
    print(f"✅ MACD calculado: {len(valid_macd)} valores válidos")
    print(f"   Warm-up period: {len(df) - len(valid_macd)} velas")

    if len(valid_macd) > 0:
        print(f"   MACD último valor: {df['macd'].iloc[-1]:.6f}")
    else:
        print("⚠️ Advertencia: No se generaron valores MACD válidos")
        return None

    # Generar nombre de archivo de salida
    output_file = processed_file.replace('_processed.csv', '_with_macd.csv')

    # Guardar dataset con MACD
    try:
        df.to_csv(output_file, index=False)
        print(f"\n💾 Dataset con MACD guardado: {output_file}")

    except Exception as e:
        print(f"❌ Error guardando archivo: {e}")
        return None

    # Mostrar estadísticas MACD
    print(f"\n📊 ESTADÍSTICAS MACD:")
    print(f"   📈 MACD:")
    print(f"      Min: {df['macd'].min():.6f}")
    print(f"      Max: {df['macd'].max():.6f}")
    print(f"      Media: {df['macd'].mean():.6f}")
    print(f"   📊 Signal:")
    print(f"      Min: {df['macd_signal'].min():.6f}")
    print(f"      Max: {df['macd_signal'].max():.6f}")
    print(f"      Media: {df['macd_signal'].mean():.6f}")
    print(f"   📉 Histogram:")
    print(f"      Min: {df['macd_histogram'].min():.6f}")
    print(f"      Max: {df['macd_histogram'].max():.6f}")
    print(f"      Media: {df['macd_histogram'].mean():.6f}")

    # Mostrar muestra de datos
    print(f"\n🔍 MUESTRA DE DATOS (últimas 3 velas):")
    columns_to_show = ['datetime', 'close', 'macd', 'macd_signal', 'macd_histogram']
    pd.set_option('display.float_format', '{:.6f}'.format)
    print(df[columns_to_show].tail(3).to_string(index=False))
    pd.reset_option('display.float_format')

    return output_file


def main():
    """Función principal"""
    print("🚀 AGREGANDO MACD AL DATASET")
    print("=" * 50)

    result_file = add_macd_to_dataset()

    if result_file:
        print("\n" + "=" * 50)
        print("✅ PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 50)
        print(f"📁 Archivo generado: {result_file}")
        print("\n💡 COLUMNAS MACD AGREGADAS:")
        print("   • macd: Línea MACD principal")
        print("   • macd_signal: Línea de señal (EMA 9)")
        print("   • macd_histogram: Histograma (MACD - Signal)")
        print("\n🎯 PRÓXIMOS PASOS:")
        print("   1. Usar archivo generado para EDA")
        print("   2. Analizar correlaciones MACD vs resultados")
        print("   3. Considerar MACD como filtro de entrada")
        print("   4. Estudiar divergencias MACD")
    else:
        print("\n❌ PROCESO FALLÓ")
        print("   Revisa los errores arriba y corrige el problema")


if __name__ == "__main__":
    main()