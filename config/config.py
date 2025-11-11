"""
Configuración del Sistema AMRS BETA1
Mean Reversion Strategy - H4 Timeframe
"""

from datetime import datetime
import MetaTrader5 as mt5

# ============================================================================
# 1. MT5 CONNECTION & DATA SOURCE
# ============================================================================
MT5_LOGIN = None  # None = usa cuenta por defecto ya logueada
MT5_PASSWORD = ""
MT5_SERVER = "FPMarkets-Demo"

SYMBOL = "USDJPY"
TIMEFRAME = mt5.TIMEFRAME_H1

# Fechas para descarga de datos (incluye warm-up de indicadores)
DATA_START_DATE = datetime(2019, 1, 1)
DATA_END_DATE = datetime(2025, 10, 25)

# Fechas para análisis de setups (período de interés real)
ANALYSIS_START_DATE = datetime(2019, 1, 1)  # ¿Es 2020?
ANALYSIS_END_DATE = datetime(2025, 10, 17)

# ============================================================================
# 2. TECHNICAL INDICATORS
# ============================================================================
EMA_PERIOD = 20
ATR_PERIOD = 20
ADX_PERIOD = 14
RSI_PERIOD = 14

# ATR Calibration (para alinear con MT5)
ATR_ADJUSTMENT_FACTOR = 0.99

# ============================================================================
# 3. TRADING STRATEGY
# ============================================================================

# ATR Levels
ATR_ENTRY_MULTIPLIER = 2.3  # Nivel de entrada desde EMA
ATR_STOP_MULTIPLIER = 3.0  # Nivel de stop loss desde EMA

# Directional Indicators Filter
#DI_THRESHOLD = 15  # Diferencia mínima entre +DI y -DI (legacy)
USE_DI_SPREAD_FILTER = True # Activar/desactivar filtro DI spread
DI_SPREAD_MAX = 15  # Máximo spread |+DI - -DI| permitido

# RSI Filter
RSI_OVERBOUGHT = 72  # Nivel para permitir shorts contra +DI extremo

# ============================================================================
# 4. FILE MANAGEMENT
# ============================================================================
DATA_FOLDER = "Data"
RESULTS_FOLDER = "results"
LOGS_FOLDER = "logs"

# Auto-generated paths
HISTORICAL_DATA_FILE = f"{DATA_FOLDER}/{SYMBOL}_H4_{DATA_START_DATE.year}-{DATA_END_DATE.year}.csv"

# ============================================================================
# 5. LOGGING & DEBUG
# ============================================================================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = f"{LOGS_FOLDER}/amrs_beta1.log"


# ============================================================================
# 6. PIP FACTOR DETECTION (Auto-detect based on symbol)
# ============================================================================
def get_pip_factor(symbol):
    """
    Obtiene el factor para convertir diferencia de precios a pips

    Args:
        symbol: Par de divisas (ej: "EURUSD", "USDJPY")

    Returns:
        int: Factor de conversión (10000 para pares 4-decimales, 100 para pares 2-decimales)
    """
    # Pares con 2 decimales (factor 100)
    two_decimal_pairs = [
        "USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CHFJPY", "CADJPY", "NZDJPY"
    ]

    # Verificar tipo de par
    if symbol.upper() in two_decimal_pairs:
        return 100
    else:
        # Default: pares con 4 decimales (factor 10000)
        return 10000


def get_symbol_info(symbol):
    """
    Obtiene información completa del símbolo

    Returns:
        dict: Información del símbolo (pip_factor, decimals, description)
    """
    pip_factor = get_pip_factor(symbol)

    if pip_factor == 100:
        decimals = 2
        description = "JPY pair (2 decimals)"
    else:
        decimals = 4
        description = "Major pair (4 decimals)"

    return {
        'pip_factor': pip_factor,
        'decimals': decimals,
        'description': description
    }

# ============================================================================
# 7. EXPERIMENTAL FLAGS (Para futuras optimizaciones)
# ============================================================================
# TODO: Agregar flags de experimentación cuando se definan
# Ejemplos:
# CHECK_ENTRY_CANDLE_SLTP = False
# ALLOW_SAME_CANDLE_CYCLE = True
# USE_DYNAMIC_TP = False