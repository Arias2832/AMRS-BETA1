"""
Detector de setups para estrategia Mean Reversion
AMRS BETA1
"""

import pandas as pd
import numpy as np


class SetupDetector:
    """Detector de setups de trading según reglas de la estrategia"""

    def __init__(self, min_candles_away=0):
        self.min_candles_away = min_candles_away
        self.setups = []

    def detect_ema_touches(self, df):
        """Detecta velas donde el precio toca la EMA20"""
        touches = (df['low'] <= df['ema20']) & (df['ema20'] <= df['high'])
        return touches

    def verify_price_moved_away(self, df, touch_idx):
        """Verifica que después del toque, el precio se alejó sin volver a tocar EMA"""
        candles_away = 0

        for i in range(touch_idx + 1, len(df)):
            if df.iloc[i]['low'] <= df.iloc[i]['ema20'] <= df.iloc[i]['high']:
                return False, candles_away
            candles_away += 1
            if candles_away >= self.min_candles_away:
                return True, candles_away

        return True, candles_away

    def detect_entry_at_atr_level(self, df, touch_idx, direction):
        """Detecta entrada en nivel ATR sin volver a tocar EMA"""
        start_idx = touch_idx + self.min_candles_away
        if start_idx == touch_idx:
            start_idx += 1

        for i in range(start_idx, len(df)):
            current_candle = df.iloc[i]

            # Verificar si NO volvió a tocar EMA
            if current_candle['low'] <= current_candle['ema20'] <= current_candle['high']:
                return False, None

            # Verificar entrada en nivel ATR
            if direction == 'LONG':
                if current_candle['low'] <= current_candle['atr_lower_entry']:
                    return True, i
            elif direction == 'SHORT':
                if current_candle['high'] >= current_candle['atr_upper_entry']:
                    return True, i

        return False, None

    def simulate_trade_outcome(self, df, entry_idx, direction, entry_price, sl_price, tp_ema_ref):
        """Simula el resultado del trade hacia adelante"""
        for i in range(entry_idx, len(df)):
            candle = df.iloc[i]

            if direction == 'LONG':
                # Stop Loss
                if candle['low'] <= sl_price:
                    return {
                        'outcome': 'LOSS',
                        'exit_date': candle['datetime'],
                        'exit_price': sl_price,
                        'pips': round((sl_price - entry_price) * 10000, 1),
                        'candles_held': i - entry_idx
                    }
                # Take Profit (toca EMA20)
                if candle['low'] <= candle['ema20'] <= candle['high']:
                    return {
                        'outcome': 'WIN',
                        'exit_date': candle['datetime'],
                        'exit_price': candle['ema20'],
                        'pips': round((candle['ema20'] - entry_price) * 10000, 1),
                        'candles_held': i - entry_idx
                    }

            elif direction == 'SHORT':
                # Stop Loss
                if candle['high'] >= sl_price:
                    return {
                        'outcome': 'LOSS',
                        'exit_date': candle['datetime'],
                        'exit_price': sl_price,
                        'pips': round((entry_price - sl_price) * 10000, 1),
                        'candles_held': i - entry_idx
                    }
                # Take Profit (toca EMA20)
                if candle['low'] <= candle['ema20'] <= candle['high']:
                    return {
                        'outcome': 'WIN',
                        'exit_date': candle['datetime'],
                        'exit_price': candle['ema20'],
                        'pips': round((entry_price - candle['ema20']) * 10000, 1),
                        'candles_held': i - entry_idx
                    }

        # No cerró (fin de datos)
        return {
            'outcome': 'OPEN',
            'exit_date': None,
            'exit_price': None,
            'pips': 0,
            'candles_held': len(df) - entry_idx
        }

    def create_setup(self, df, touch_idx, entry_idx, direction):
        """Crea un setup con toda la información necesaria"""
        entry_candle = df.iloc[entry_idx]
        touch_candle = df.iloc[touch_idx]

        if direction == 'LONG':
            entry_price = entry_candle['atr_lower_entry']
            sl_price = entry_candle['atr_lower_3']
            tp_price_ref = entry_candle['ema20']
        elif direction == 'SHORT':
            entry_price = entry_candle['atr_upper_entry']
            sl_price = entry_candle['atr_upper_3']
            tp_price_ref = entry_candle['ema20']

        sl_distance = abs(entry_price - sl_price)
        tp_distance_estimated = abs(entry_price - tp_price_ref)
        rr_ratio_estimated = tp_distance_estimated / sl_distance if sl_distance > 0 else 0

        trade_result = self.simulate_trade_outcome(
            df, entry_idx, direction, entry_price, sl_price, tp_price_ref
        )

        if trade_result['outcome'] in ['WIN', 'LOSS']:
            rr_ratio_real = abs(trade_result['pips']) / (sl_distance * 10000)
        else:
            rr_ratio_real = None

        setup = {
            'touch_date': touch_candle['datetime'],
            'entry_date': entry_candle['datetime'],
            'exit_date': trade_result['exit_date'],
            'direction': direction,
            'entry_price': round(entry_price, 5),
            'sl_price': round(sl_price, 5),
            'tp_price_ref': round(tp_price_ref, 5),
            'exit_price': round(trade_result['exit_price'], 5) if trade_result['exit_price'] else None,
            'sl_pips': round(sl_distance * 10000, 1),
            'tp_pips_estimated': round(tp_distance_estimated * 10000, 1),
            'result_pips': trade_result['pips'],
            'rr_ratio_estimated': round(rr_ratio_estimated, 2),
            'rr_ratio_real': round(rr_ratio_real, 2) if rr_ratio_real else None,
            'outcome': trade_result['outcome'],
            'candles_away': entry_idx - touch_idx,
            'candles_held': trade_result['candles_held'],
            'adx': round(entry_candle['adx'], 2),
            'plus_di': round(entry_candle['plus_di'], 2),
            'minus_di': round(entry_candle['minus_di'], 2),
            'rsi': round(entry_candle['rsi'], 2),
            'atr': round(entry_candle['atr'], 5)
        }

        return setup

    def detect_all_setups(self, df, start_date=None, end_date=None):
        """Detecta todos los setups válidos en el DataFrame"""
        print("\n🔍 Detectando setups...")

        df = df.reset_index(drop=True)
        df_full = df.copy()

        df_analysis = df_full.copy()
        if start_date:
            df_analysis = df_analysis[df_analysis['datetime'] >= start_date]
        if end_date:
            df_analysis = df_analysis[df_analysis['datetime'] <= end_date]
        df_analysis = df_analysis.reset_index(drop=True)

        ema_touches = self.detect_ema_touches(df_analysis)
        touch_dates = df_analysis[ema_touches]['datetime'].tolist()

        self.setups = []

        for touch_date in touch_dates:
            matches = df_full.index[df_full['datetime'] == touch_date].tolist()
            if not matches:
                continue
            touch_idx = matches[0]

            if self.min_candles_away > 0:
                is_valid, candles_away = self.verify_price_moved_away(df_full, touch_idx)
                if not is_valid or candles_away < self.min_candles_away:
                    continue

            # Buscar entrada LONG
            found_long, entry_idx = self.detect_entry_at_atr_level(df_full, touch_idx, 'LONG')
            if found_long:
                entry_date = df_full.iloc[entry_idx]['datetime']
                if (not start_date or entry_date >= start_date) and (not end_date or entry_date <= end_date):
                    setup = self.create_setup(df_full, touch_idx, entry_idx, 'LONG')
                    self.setups.append(setup)

            # Buscar entrada SHORT
            found_short, entry_idx = self.detect_entry_at_atr_level(df_full, touch_idx, 'SHORT')
            if found_short:
                entry_date = df_full.iloc[entry_idx]['datetime']
                if (not start_date or entry_date >= start_date) and (not end_date or entry_date <= end_date):
                    setup = self.create_setup(df_full, touch_idx, entry_idx, 'SHORT')
                    self.setups.append(setup)

        print(f"✅ {len(self.setups)} setups encontrados")
        return self.setups

    def print_setups(self):
        """Imprime todos los setups encontrados"""
        if not self.setups:
            print("\n❌ No se encontraron setups")
            return

        print("\n" + "=" * 70)
        print(f"SETUPS ENCONTRADOS: {len(self.setups)}")
        print("=" * 70)

        wins = sum(1 for s in self.setups if s['outcome'] == 'WIN')
        losses = sum(1 for s in self.setups if s['outcome'] == 'LOSS')
        open_trades = sum(1 for s in self.setups if s['outcome'] == 'OPEN')

        print(f"\n📊 Resultados: {wins} ganadores | {losses} perdedores | {open_trades} abiertos")

        for i, setup in enumerate(self.setups, 1):
            outcome_emoji = {'WIN': '✅', 'LOSS': '❌', 'OPEN': '⏳'}
            print(f"\n{outcome_emoji.get(setup['outcome'], '❓')} SETUP #{i} - {setup['outcome']}")
            print("-" * 70)
            print(f"  📅 Toque EMA:         {setup['touch_date']}")
            print(f"  📅 Entrada:           {setup['entry_date']}")
            print(f"  📅 Salida:            {setup['exit_date'] if setup['exit_date'] else 'N/A'}")
            print(f"  📊 Dirección:         {setup['direction']}")
            print(f"  💰 Precio entrada:    {setup['entry_price']}")
            print(f"  🛑 Stop Loss:         {setup['sl_price']} ({setup['sl_pips']} pips)")
            print(f"  🎯 TP referencia:     {setup['tp_price_ref']} ({setup['tp_pips_estimated']} pips)")
            print(f"  💵 Precio salida:     {setup['exit_price'] if setup['exit_price'] else 'N/A'}")
            print(f"  📈 R:R estimado:      {setup['rr_ratio_estimated']}:1")
            print(f"  📈 R:R real:          {setup['rr_ratio_real']}:1" if setup['rr_ratio_real'] else "  📈 R:R real:          N/A")
            print(f"  💵 Resultado:         {setup['result_pips']:+.1f} pips")
            print(f"  🕐 Velas alejadas:    {setup['candles_away']}")
            print(f"  🕐 Velas en trade:    {setup['candles_held']}")
            print(f"  📊 ADX:               {setup['adx']}")
            print(f"  📊 +DI / -DI:         {setup['plus_di']} / {setup['minus_di']}")
            print(f"  📊 RSI:               {setup['rsi']}")

    def export_to_csv(self, filename):
        """Exporta setups a CSV para análisis"""
        if not self.setups:
            print("\n❌ No hay setups para exportar")
            return

        df = pd.DataFrame(self.setups)
        df.to_csv(filename, index=False)
        print(f"\n💾 Setups exportados: {filename}")