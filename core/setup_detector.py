"""
Detector de setups para estrategia Mean Reversion
AMRS BETA1
"""

import pandas as pd
import numpy as np


class SetupDetector:
    """Detector de setups de trading según reglas de la estrategia"""

    def __init__(self, min_candles_away=0):
        """
        Inicializa el detector

        Args:
            min_candles_away: Mínimo de velas alejadas de EMA después del toque
        """
        self.min_candles_away = min_candles_away
        self.setups = []

    def detect_ema_touches(self, df):
        """
        Detecta velas donde el precio toca la EMA20

        Args:
            df: DataFrame con indicadores

        Returns:
            pd.Series: Boolean series donde True = toca EMA
        """
        # Toca EMA si Low <= EMA <= High
        touches = (df['low'] <= df['ema20']) & (df['ema20'] <= df['high'])
        return touches

    def verify_price_moved_away(self, df, touch_idx):
        """
        Verifica que después del toque, el precio se alejó sin volver a tocar EMA

        Args:
            df: DataFrame con indicadores
            touch_idx: Índice de la vela donde tocó EMA

        Returns:
            tuple: (bool: es_valido, int: velas_alejadas)
        """
        # Revisar velas después del toque
        candles_away = 0

        for i in range(touch_idx + 1, len(df)):
            # Verificar si vuelve a tocar EMA
            if df.iloc[i]['low'] <= df.iloc[i]['ema20'] <= df.iloc[i]['high']:
                # Volvió a tocar, setup inválido
                return False, candles_away

            candles_away += 1

            # Si ya se alejó suficientes velas, podemos buscar entrada
            if candles_away >= self.min_candles_away:
                return True, candles_away

        # Llegó al final sin encontrar entrada
        return True, candles_away

    def detect_entry_at_atr_level(self, df, touch_idx, direction):
        print(f"[DEBUG] min_candles_away = {self.min_candles_away}")
        # Asegurar índices consecutivos para no saltar velas
        #df = df.reset_index(drop=True)

        # Buscar desde touch_idx + min_candles_away en adelante
        start_idx = touch_idx + self.min_candles_away
        if start_idx == touch_idx:
            start_idx += 1

        for i in range(start_idx, len(df)):
            current_candle = df.iloc[i]

            # DEBUG - Solo para toque del 03-20 08:00
            touch_candle = df.iloc[touch_idx]
            if '2025-03-20 08:00' in str(touch_candle['datetime']) and direction == 'LONG' and i < touch_idx + 20:
                print(f"\n  Vela #{i}: {current_candle['datetime']}")
                print(f"    Low: {current_candle['low']:.5f}")
                print(f"    ATR-2.2: {current_candle['atr_lower_2_2']:.5f}")
                print(f"    ¿Toca ATR-2.2? {current_candle['low'] <= current_candle['atr_lower_2_2']}")
                print(f"    EMA20: {current_candle['ema20']:.5f}")
                print(f"    ¿Toca EMA? {current_candle['low'] <= current_candle['ema20'] <= current_candle['high']}")

            # Verificar si NO volvió a tocar EMA
            if current_candle['low'] <= current_candle['ema20'] <= current_candle['high']:
                # Volvió a tocar EMA, setup cancelado
                return False, None

            # Verificar si alcanza nivel de entrada (ATR±2.2)
            # LONG: Precio bajó a ATR-2.2 (sobreextendido abajo, reversión hacia arriba)
            if direction == 'LONG':
                if current_candle['low'] <= current_candle['atr_lower_2_2']:
                    return True, i

            # SHORT: Precio subió a ATR+2.2 (sobreextendido arriba, reversión hacia abajo)
            elif direction == 'SHORT':
                if current_candle['high'] >= current_candle['atr_upper_2_2']:
                    return True, i

        return False, None

    def simulate_trade_outcome(self, df, entry_idx, direction, entry_price, sl_price, tp_ema_ref):
        """
        Simula el resultado del trade hacia adelante

        Args:
            df: DataFrame completo
            entry_idx: Índice de entrada
            direction: 'LONG' o 'SHORT'
            entry_price: Precio de entrada
            sl_price: Precio de stop loss (fijo)
            tp_ema_ref: Precio EMA20 de referencia en entrada

        Returns:
            dict: Resultado del trade (ganador/perdedor, pips, velas)
        """
        # Simular vela por vela desde la entrada
        for i in range(entry_idx + 1, len(df)):
            candle = df.iloc[i]

            # Verificar si toca STOP LOSS primero (SL es fijo)
            if direction == 'LONG':
                # LONG: SL está abajo
                if candle['low'] <= sl_price:
                    return {
                        'outcome': 'LOSS',
                        'exit_date': candle['datetime'],
                        'exit_price': sl_price,
                        'pips': round((sl_price - entry_price) * 10000, 1),
                        'candles_held': i - entry_idx
                    }

                # LONG: TP cuando toca EMA20
                if candle['low'] <= candle['ema20'] <= candle['high']:
                    return {
                        'outcome': 'WIN',
                        'exit_date': candle['datetime'],
                        'exit_price': candle['ema20'],
                        'pips': round((candle['ema20'] - entry_price) * 10000, 1),
                        'candles_held': i - entry_idx
                    }

            elif direction == 'SHORT':
                # SHORT: SL está arriba
                if candle['high'] >= sl_price:
                    return {
                        'outcome': 'LOSS',
                        'exit_date': candle['datetime'],
                        'exit_price': sl_price,
                        'pips': round((entry_price - sl_price) * 10000, 1),
                        'candles_held': i - entry_idx
                    }

                # SHORT: TP cuando toca EMA20
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
        """
        Crea un setup con toda la información necesaria

        Args:
            df: DataFrame con indicadores
            touch_idx: Índice del toque de EMA
            entry_idx: Índice de la entrada
            direction: 'LONG' o 'SHORT'

        Returns:
            dict: Setup completo con precios, niveles, indicadores, resultado
        """
        entry_candle = df.iloc[entry_idx]
        touch_candle = df.iloc[touch_idx]

        # Calcular precios de entrada y SL según dirección
        if direction == 'LONG':
            # LONG: Precio bajó a ATR-2.2, SL en ATR-3, TP en EMA
            entry_price = entry_candle['atr_lower_2_2']
            sl_price = entry_candle['atr_lower_3']
            tp_price_ref = entry_candle['ema20']  # Referencia para R:R

        elif direction == 'SHORT':
            # SHORT: Precio subió a ATR+2.2, SL en ATR+3, TP en EMA
            entry_price = entry_candle['atr_upper_2_2']
            sl_price = entry_candle['atr_upper_3']
            tp_price_ref = entry_candle['ema20']  # Referencia para R:R

        # Calcular R:R estimado (usando EMA en momento de entrada)
        sl_distance = abs(entry_price - sl_price)
        tp_distance_estimated = abs(entry_price - tp_price_ref)
        rr_ratio_estimated = tp_distance_estimated / sl_distance if sl_distance > 0 else 0

        # Simular resultado real del trade
        trade_result = self.simulate_trade_outcome(
            df, entry_idx, direction, entry_price, sl_price, tp_price_ref
        )

        # Calcular R:R real si el trade cerró
        if trade_result['outcome'] in ['WIN', 'LOSS']:
            rr_ratio_real = abs(trade_result['pips']) / (sl_distance * 10000)
        else:
            rr_ratio_real = None

        setup = {
            # Fechas
            'touch_date': touch_candle['datetime'],
            'entry_date': entry_candle['datetime'],
            'exit_date': trade_result['exit_date'],

            # Trade info
            'direction': direction,
            'entry_price': round(entry_price, 5),
            'sl_price': round(sl_price, 5),
            'tp_price_ref': round(tp_price_ref, 5),
            'exit_price': round(trade_result['exit_price'], 5) if trade_result['exit_price'] else None,

            # Distancias
            'sl_pips': round(sl_distance * 10000, 1),
            'tp_pips_estimated': round(tp_distance_estimated * 10000, 1),
            'result_pips': trade_result['pips'],

            # Ratios
            'rr_ratio_estimated': round(rr_ratio_estimated, 2),
            'rr_ratio_real': round(rr_ratio_real, 2) if rr_ratio_real else None,

            # Resultado
            'outcome': trade_result['outcome'],
            'candles_away': entry_idx - touch_idx,
            'candles_held': trade_result['candles_held'],

            # Indicadores EN EL MOMENTO DE LA ENTRADA
            'adx': round(entry_candle['adx'], 2),
            'plus_di': round(entry_candle['plus_di'], 2),
            'minus_di': round(entry_candle['minus_di'], 2),
            'rsi': round(entry_candle['rsi'], 2),
            'atr': round(entry_candle['atr'], 5)
        }

        return setup

    def detect_all_setups(self, df, start_date=None, end_date=None):
        """
        Detecta todos los setups válidos en el DataFrame
        """
        print("\n🔍 Detectando setups...")

        # Asegurar que todo el DataFrame tenga índices consecutivos
        df = df.reset_index(drop=True)
        df_full = df.copy()

        # Filtrar por fechas
        df_analysis = df_full.copy()
        if start_date:
            df_analysis = df_analysis[df_analysis['datetime'] >= start_date]
        if end_date:
            df_analysis = df_analysis[df_analysis['datetime'] <= end_date]
        df_analysis = df_analysis.reset_index(drop=True)

        print(f"   Período análisis: {df_analysis['datetime'].iloc[0]} a {df_analysis['datetime'].iloc[-1]}")
        print(f"   Velas a analizar: {len(df_analysis)}")

        # Detectar toques de EMA en período filtrado
        ema_touches = self.detect_ema_touches(df_analysis)
        touch_dates = df_analysis[ema_touches]['datetime'].tolist()
        print(f"   Toques de EMA encontrados: {len(touch_dates)}")

        self.setups = []

        # Procesar cada toque de EMA
        for touch_date in touch_dates:
            # Recalcular touch_idx siempre en df_full sincronizado
            matches = df_full.index[df_full['datetime'] == touch_date].tolist()
            if not matches:
                continue
            touch_idx = matches[0]

            # DEBUG opcional
            if '2025-03-20' in str(touch_date):
                print(f"\n🔍 DEBUG TOQUE 03-20:")
                print(f"   Touch date: {touch_date}")
                print(f"   touch_idx: {touch_idx}")
                if touch_idx + 1 < len(df_full):
                    print(f"   Siguiente vela: {df_full.iloc[touch_idx + 1]['datetime']}")
                if touch_idx + 2 < len(df_full):
                    print(f"   Vela +2: {df_full.iloc[touch_idx + 2]['datetime']}")

            # Verificar alejamiento (solo si se usa)
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

        print(f"✅ Setups válidos encontrados: {len(self.setups)}")
        return self.setups

    def print_setups(self):
        """Imprime todos los setups encontrados de forma legible"""
        if not self.setups:
            print("\n❌ No se encontraron setups en el período especificado")
            return

        print("\n" + "=" * 70)
        print(f"SETUPS ENCONTRADOS: {len(self.setups)}")
        print("=" * 70)

        wins = sum(1 for s in self.setups if s['outcome'] == 'WIN')
        losses = sum(1 for s in self.setups if s['outcome'] == 'LOSS')
        open_trades = sum(1 for s in self.setups if s['outcome'] == 'OPEN')

        print(f"\n📊 Resultados: {wins} ganadores | {losses} perdedores | {open_trades} abiertos")

        for i, setup in enumerate(self.setups, 1):
            outcome_emoji = {
                'WIN': '✅',
                'LOSS': '❌',
                'OPEN': '⏳'
            }

            print(f"\n{outcome_emoji.get(setup['outcome'], '❓')} SETUP #{i} - {setup['outcome']}")
            print("-" * 70)
            print(f"  📅 Toque EMA:         {setup['touch_date']}")
            print(f"  📅 Entrada:           {setup['entry_date']}")
            print(f"  📅 Salida:            {setup['exit_date'] if setup['exit_date'] else 'N/A'}")
            print(f"  📊 Dirección:         {setup['direction']}")
            print(f"  💰 Precio entrada:    {setup['entry_price']}")
            print(f"  🛑 Stop Loss (fijo):  {setup['sl_price']} ({setup['sl_pips']} pips)")
            print(f"  🎯 TP referencia EMA: {setup['tp_price_ref']} ({setup['tp_pips_estimated']} pips)")
            print(f"  💵 Precio salida:     {setup['exit_price'] if setup['exit_price'] else 'N/A'}")
            print(f"  📈 R:R estimado:      {setup['rr_ratio_estimated']}:1")
            print(f"  📈 R:R real:          {setup['rr_ratio_real']}:1" if setup[
                'rr_ratio_real'] else "  📈 R:R real:          N/A")
            print(f"  💵 Resultado:         {setup['result_pips']:+.1f} pips")
            print(f"  🕐 Velas alejadas:    {setup['candles_away']}")
            print(f"  🕐 Velas en trade:    {setup['candles_held']}")
            print(f"  📊 ADX:               {setup['adx']}")
            print(f"  📊 +DI / -DI:         {setup['plus_di']} / {setup['minus_di']}")
            print(f"  📊 RSI:               {setup['rsi']}")

    def export_to_csv(self, filename):
        """
        Exporta setups a CSV para análisis

        Args:
            filename: Nombre del archivo CSV
        """
        if not self.setups:
            print("\n❌ No hay setups para exportar")
            return

        df = pd.DataFrame(self.setups)
        df.to_csv(filename, index=False)
        print(f"\n💾 Setups exportados a: {filename}")