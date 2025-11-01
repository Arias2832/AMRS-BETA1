"""
Configuración del Sistema AMRS BETA1
Mean Reversion Strategy - H4 Timeframe
"""

from datetime import datetime
import MetaTrader5 as mt5

# ============================================================
# CONFIGURACIÓN MT5
# ============================================================
MT5_LOGIN = None  # None = usa cuenta por defecto ya logueada
MT5_PASSWORD = ""
MT5_SERVER = "FPMarkets-Demo"  # Ajustar si es necesario

# ============================================================
# DATOS HISTÓRICOS
# ============================================================
SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_H4

# Fechas de descarga (incluye margen para warm-up de indicadores)
START_DATE = datetime(2019, 1, 1)
END_DATE = datetime(2025, 10, 25)

# ============================================================
# PARÁMETROS DE INDICADORES
# ============================================================
EMA_PERIOD = 20
ATR_PERIOD = 20  # Cambiado de 14 a 20 para coincidir con MT5
ADX_PERIOD = 14
RSI_PERIOD = 14

# Factor de ajuste ATR (para calibrar con MT5)
# Calibrado con ATR nativo de MT5 (0.00393 vs Python 0.00351)
ATR_ADJUSTMENT_FACTOR = 0.99  # Factor: 0.00393 / 0.00351 = 1.12

# ============================================================
# PARÁMETROS DE ESTRATEGIA
# ============================================================
# Bandas ATR
ATR_ENTRY_MULTIPLIER = 2.3  # Nivel de entrada
ATR_STOP_MULTIPLIER = 3.0   # Nivel de stop loss

# Filtros DI
DI_THRESHOLD = 15  # Diferencia mínima entre +DI y -DI para filtrar

# Filtro RSI (excepción para DI extremo)
RSI_OVERBOUGHT = 72  # Nivel de agotamiento para permitir shorts contra +DI extremo

# ============================================================
# RUTAS DE ARCHIVOS
# ============================================================
DATA_FOLDER = "Data"
RESULTS_FOLDER = "results"
LOGS_FOLDER = "logs"

# Nombre del archivo de datos históricos
HISTORICAL_DATA_FILE = f"{DATA_FOLDER}/{SYMBOL}_H4_{START_DATE.year}-{END_DATE.year}.csv"

# ============================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = f"{LOGS_FOLDER}/amrs_beta1.log"