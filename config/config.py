"""
Configuración del Sistema AMRS BETA1
Mean Reversion Strategy - H4 Timeframe
"""

from datetime import datetime
import MetaTrader5 as mt5

# MT5 Configuration
MT5_LOGIN = None  # None = usa cuenta por defecto ya logueada
MT5_PASSWORD = ""
MT5_SERVER = "FPMarkets-Demo"

# Historical Data
SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_H4
START_DATE = datetime(2019, 1, 1)
END_DATE = datetime(2025, 10, 25)

# Indicator Parameters
EMA_PERIOD = 20
ATR_PERIOD = 20
ADX_PERIOD = 14
RSI_PERIOD = 14
ATR_ADJUSTMENT_FACTOR = 0.99

# Strategy Parameters
ATR_ENTRY_MULTIPLIER = 2.2
ATR_STOP_MULTIPLIER = 3.0
DI_THRESHOLD = 15
RSI_OVERBOUGHT = 72

# File Paths
DATA_FOLDER = "Data"
RESULTS_FOLDER = "results"
LOGS_FOLDER = "logs"
HISTORICAL_DATA_FILE = f"{DATA_FOLDER}/{SYMBOL}_H4_{START_DATE.year}-{END_DATE.year}.csv"

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = f"{LOGS_FOLDER}/amrs_beta1.log"