"""
Detector de setups para estrategia Mean Reversion
AMRS BETA1
"""

import pandas as pd
import numpy as np


class SetupDetector:
    """Detector de setups de trading según reglas de la estrategia"""

    def __init__(self, min_candles_away=0, use_di_filter=False, di_spread_max=20):
        self.min_candles_away = min_candles_away
        self.use_di_filter = use_di_filter
        self.di_spread_max = di_spread_max
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

    def check_di_spread_filter(self, candle):
        """Verifica si el filtro DI spread pasa para la vela dada"""
        if not self.use_di_filter:
            return True

        di_spread = abs(candle['plus_di'] - candle['minus_di'])
        return di_spread < self.di_spread_max

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

            # Aplicar filtro DI spread si está habilitado
            if not self.check_di_spread_filter(current_candle):
                continue  # Saltar esta vela, no cumple filtro DI

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
            print(f"  📈 R:R real:          {setup['rr_ratio_real']}:1" if setup[
                'rr_ratio_real'] else "  📈 R:R real:          N/A")
            print(f"  💵 Resultado:         {setup['result_pips']:+.1f} pips")
            print(f"  🕐 Velas alejadas:    {setup['candles_away']}")
            print(f"  🕐 Velas en trade:    {setup['candles_held']}")
            print(f"  📊 ADX:               {setup['adx']}")
            print(f"  📊 +DI / -DI:         {setup['plus_di']} / {setup['minus_di']}")
            print(f"  📊 RSI:               {setup['rsi']}")

    def get_executive_summary(self, symbol, start_date, end_date):
        """Genera resumen ejecutivo con métricas clave"""
        if not self.setups:
            print("\n❌ No hay setups para analizar")
            return

        # Calcular métricas básicas
        total_trades = len(self.setups)
        wins = [s for s in self.setups if s['outcome'] == 'WIN']
        losses = [s for s in self.setups if s['outcome'] == 'LOSS']
        open_trades = [s for s in self.setups if s['outcome'] == 'OPEN']

        win_count = len(wins)
        loss_count = len(losses)
        closed_trades = win_count + loss_count

        if closed_trades == 0:
            print("\n⚠️ No hay trades cerrados para analizar")
            return

        # Win Rate
        win_rate = (win_count / closed_trades) * 100

        # Pips totales
        total_pips = sum(s['result_pips'] for s in wins + losses)
        win_pips_total = sum(s['result_pips'] for s in wins)
        loss_pips_total = sum(s['result_pips'] for s in losses)

        # Promedios
        avg_win_pips = win_pips_total / win_count if win_count > 0 else 0
        avg_loss_pips = abs(loss_pips_total) / loss_count if loss_count > 0 else 0

        # Esperanza matemática - Método 1 (directo)
        expectativa_directa = total_pips / closed_trades

        # Esperanza matemática - Método 2 (probabilístico)
        win_prob = win_count / closed_trades
        loss_prob = loss_count / closed_trades
        expectativa_probabilistica = (win_prob * avg_win_pips) - (loss_prob * avg_loss_pips)

        # Promedio de ambos métodos
        expectativa_promedio = (expectativa_directa + expectativa_probabilistica) / 2

        # Profit Factor
        profit_factor = win_pips_total / abs(loss_pips_total) if loss_pips_total != 0 else float('inf')

        # Max Drawdown (aproximado - mayor pérdida individual)
        max_drawdown = min(s['result_pips'] for s in losses) if losses else 0

        # Trades por año
        years = (end_date - start_date).days / 365.25
        trades_per_year = closed_trades / years if years > 0 else 0

        # Expectativa anual
        expectativa_anual = expectativa_promedio * trades_per_year

        # Veredicto
        if expectativa_promedio > 15 and profit_factor > 2.5 and win_rate > 65:
            veredicto = "✅ EXCELENTE"
        elif expectativa_promedio > 8 and profit_factor > 1.8 and win_rate > 55:
            veredicto = "🟡 PROMETEDORA"
        elif expectativa_promedio > 3 and profit_factor > 1.3:
            veredicto = "⚠️ MARGINAL"
        else:
            veredicto = "❌ DESCARTADA"

        # Mostrar resumen
        period_str = f"{start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}"
        years_str = f"{years:.1f} años" if years >= 1 else f"{years * 12:.1f} meses"

        print("\n" + "=" * 70)
        print(f"📈 RESUMEN EJECUTIVO - {symbol} ({years_str})")
        print("=" * 70)
        print(f"💰 Pips Netos: {total_pips:+.0f} pips")
        print(f"✅ Win Rate: {win_rate:.0f}% ({win_count}W | {loss_count}L)")
        if open_trades:
            print(f"⏳ Trades abiertos: {len(open_trades)}")
        print(f"📊 Trades promedio: {trades_per_year:.0f}/año ({closed_trades} total)")

        print(f"\n🧮 ESPERANZA MATEMÁTICA:")
        print(f"   📍 Método directo: {expectativa_directa:+.2f} pips/trade ({total_pips:.0f} ÷ {closed_trades})")
        print(f"   📍 Método probabilístico: {expectativa_probabilistica:+.2f} pips/trade*")
        print(f"   🎯 Promedio: {expectativa_promedio:+.2f} pips/trade")

        print(f"\n📈 BREAKDOWN POR TIPO:")
        print(f"   🟢 Avg Win: +{avg_win_pips:.1f} pips/trade ganador")
        print(f"   🔴 Avg Loss: -{avg_loss_pips:.1f} pips/trade perdedor")

        print(f"\n📊 MÉTRICAS CLAVE:")
        print(f"   💪 Profit Factor: {profit_factor:.2f}")
        print(f"   ⚠️ Max Drawdown: {max_drawdown:+.0f} pips")
        print(
            f"   📈 Expectativa anual: {expectativa_anual:+.0f} pips ({expectativa_promedio:+.1f} × {trades_per_year:.0f})")

        print(f"\n🚦 VEREDICTO: {veredicto}")
        if veredicto == "✅ EXCELENTE":
            print("   ✅ Expectativa excelente (>+15 pips)")
            print("   ✅ Profit factor sólido (>2.5)")
            print("   ✅ Win rate alto (>65%)")
        elif veredicto == "🟡 PROMETEDORA":
            print("   ✅ Expectativa positiva sólida")
            print("   ✅ Métricas balanceadas")
            print("   🎯 Vale la pena optimizar")
        elif veredicto == "⚠️ MARGINAL":
            print("   ⚠️ Expectativa baja pero positiva")
            print("   🔧 Requiere optimización")
        else:
            print("   ❌ Expectativa negativa o muy baja")
            print("   🚫 No recomendada sin cambios mayores")

        print(
            f"\n*Cálculo: ({win_rate:.0f}% × {avg_win_pips:.1f}) - ({100 - win_rate:.0f}% × {avg_loss_pips:.1f}) = {expectativa_probabilistica:+.2f}")
        print("=" * 70)

    def export_to_csv(self, filename):
        """Exporta setups a CSV para análisis"""
        if not self.setups:
            print("\n❌ No hay setups para exportar")
            return

        df = pd.DataFrame(self.setups)
        df.to_csv(filename, index=False)
        print(f"\n💾 Setups exportados: {filename}")