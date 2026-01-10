class RiskManager:
    MAX_RISK_PER_TRADE = 0.01  # 1% of Capital
    
    def __init__(self):
        pass

    def calculate_trade(self, entry_price, capital, is_short, atr):
        # ATR-based Dynamic SL (2x ATR)
        sl_distance = atr * 2
        
        if is_short:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - (sl_distance * 2)
        else:
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + (sl_distance * 2)

        # Margin Management: Use exactly 1% of the wallet as margin for the initial entry
        # Value = Capital * 0.01 * Leverage (Assume 20x for calculation)
        margin_percent = 0.01
        leverage = 20
        trade_value = capital * margin_percent * leverage
        quantity = trade_value / entry_price

        return {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'quantity': quantity,
            'is_short': is_short
        }

    def should_confirm_entry(self, last_candle, is_bullish_signal):
        # Institutional Rule: Wait for Candle Close confirmation
        # last_candle should be a dict with 'close', 'open'
        is_bullish = last_candle['close'] > last_candle['open']
        if is_bullish_signal:
            return is_bullish
        return not is_bullish

    def calculate_trailing_stop(self, current_price, last_stop_loss, is_short):
        if is_short:
            potential_new_sl = current_price * 1.01
            if potential_new_sl < last_stop_loss:
                return potential_new_sl
        else:
            potential_new_sl = current_price * 0.99
            if potential_new_sl > last_stop_loss:
                return potential_new_sl
        return last_stop_loss
