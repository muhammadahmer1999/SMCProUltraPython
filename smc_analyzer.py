import pandas as pd
import numpy as np

class SMCAnalyzer:
    def __init__(self):
        self.swing_points = []
        self.order_blocks = []
        self.fvgs = []
        self.liquidity_pools = []
        self.has_choch = False
        self.has_idm = False

    def analyze(self, df):
        if len(df) < 20:
            return

        self.identify_market_structure(df)
        self.identify_order_blocks(df)
        self.identify_fvgs(df)
        self.identify_liquidity(df)
        self.check_institutional_signals(df)

    def identify_market_structure(self, df):
        self.swing_points = []
        self.has_choch = False
        
        # We need at least a few candles to check left/right
        for i in range(5, len(df) - 5):
            high = df.iloc[i]['high']
            low = df.iloc[i]['low']
            
            # Swing High (5-candle window parity)
            if high > df.iloc[i-1]['high'] and high > df.iloc[i-2]['high'] and \
               high > df.iloc[i+1]['high'] and high > df.iloc[i+2]['high']:
                
                point_type = "HH"
                if self.swing_points:
                    last_highs = [s for s in self.swing_points if s['type'] in ["HH", "LH"]]
                    if last_highs:
                        last_high = last_highs[-1]
                        point_type = "HH" if high > last_high['price'] else "LH"
                        
                        # BOS & CHoCH Logic
                        if high > last_high['price']:
                            if last_high['type'] == "LH":
                                self.swing_points.append({'price': float(high), 'index': i, 'type': "BOS_BULL"})
                            elif any(s['type'] == "LL" for s in self.swing_points):
                                self.has_choch = True
                
                self.swing_points.append({'price': float(high), 'index': i, 'type': point_type})

            # Swing Low (5-candle window parity)
            if low < df.iloc[i-1]['low'] and low < df.iloc[i-2]['low'] and \
               low < df.iloc[i+1]['low'] and low < df.iloc[i+2]['low']:
                
                point_type = "LL"
                if self.swing_points:
                    last_lows = [s for s in self.swing_points if s['type'] in ["LL", "HL"]]
                    if last_lows:
                        last_low = last_lows[-1]
                        point_type = "LL" if low < last_low['price'] else "HL"
                        
                        if low < last_low['price']:
                            if last_low['type'] == "HL":
                                self.swing_points.append({'price': float(low), 'index': i, 'type': "BOS_BEAR"})
                
                self.swing_points.append({'price': float(low), 'index': i, 'type': point_type})

    def check_institutional_signals(self, df):
        self.has_idm = False
        if len(self.swing_points) >= 2:
            last_leg = self.swing_points[-2:]
            current_low = df.iloc[-1]['low']
            current_close = df.iloc[-1]['close']
            
            # IDM: Sweep of first internal pullback
            if current_low < last_leg[0]['price'] and current_close > last_leg[0]['price']:
                self.has_idm = True

    def is_in_discount(self, current_price, bullish):
        if len(self.swing_points) < 2:
            return True
            
        highs = [s['price'] for s in self.swing_points if s['type'] == "HH"]
        lows = [s['price'] for s in self.swing_points if s['type'] == "LL"]
        
        high = highs[-1] if highs else current_price
        low = lows[-1] if lows else current_price
        mid = (high + low) / 2
        
        return current_price < mid if bullish else current_price > mid

    def identify_order_blocks(self, df):
        self.order_blocks = []
        for i in range(1, len(df) - 3):
            # Bullish OB (Down candle before big up move)
            body_size = abs(df.iloc[i]['close'] - df.iloc[i]['open'])
            is_bearish = df.iloc[i]['close'] < df.iloc[i]['open']
            is_bullish = df.iloc[i]['close'] > df.iloc[i]['open']
            
            if is_bearish and df.iloc[i+1]['close'] > df.iloc[i]['high'] and \
               (df.iloc[i+2]['close'] - df.iloc[i+1]['open']) > body_size * 2:
                self.order_blocks.append({'high': float(df.iloc[i]['high']), 'low': float(df.iloc[i]['low']), 'bullish': True, 'migitated': False})

            # Bearish OB
            if is_bullish and df.iloc[i+1]['close'] < df.iloc[i]['low'] and \
               (df.iloc[i+1]['open'] - df.iloc[i+2]['close']) > body_size * 2:
                self.order_blocks.append({'high': float(df.iloc[i]['high']), 'low': float(df.iloc[i]['low']), 'bullish': False, 'migitated': False})

    def identify_fvgs(self, df):
        self.fvgs = []
        for i in range(len(df) - 2):
            # Bullish FVG
            if df.iloc[i+2]['low'] > df.iloc[i]['high']:
                self.fvgs.append({'bottom': float(df.iloc[i]['high']), 'top': float(df.iloc[i+2]['low']), 'bullish': True})
            
            # Bearish FVG
            if df.iloc[i]['low'] > df.iloc[i+2]['high']:
                self.fvgs.append({'top': float(df.iloc[i]['low']), 'bottom': float(df.iloc[i+2]['high']), 'bullish': False})

    def identify_liquidity(self, df):
        self.liquidity_pools = []
        # Parallel logic to C#: check last 20 candles for equal highs/lows
        for i in range(2, len(df) - 2):
            curr_high = df.iloc[i]['high']
            curr_low = df.iloc[i]['low']
            for j in range(max(0, i - 20), i - 2):
                if abs(curr_high - df.iloc[j]['high']) / curr_high < 0.001:
                    self.liquidity_pools.append(float(curr_high))
                if abs(curr_low - df.iloc[j]['low']) / curr_low < 0.001:
                    self.liquidity_pools.append(float(curr_low))

    def is_inside_ob(self, price, bullish):
        for ob in self.order_blocks:
            if ob['bullish'] == bullish and not ob['migitated'] and price >= ob['low'] and price <= ob['high']:
                return True
        return False

    def is_price_in_fvg(self, price, bullish):
        for fvg in self.fvgs:
            if fvg['bullish'] == bullish and price >= fvg['bottom'] and price <= fvg['top']:
                return True
        return False
