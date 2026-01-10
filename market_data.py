import ccxt.async_support as ccxt
import pandas as pd
import asyncio

class MarketDataManager:
    def __init__(self, api_key="", api_secret=""):
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        # Set to Testnet if needed (mirroring C# parity)
        self.exchange.set_sandbox_mode(True)

    async def close(self):
        await self.exchange.close()

    async def get_balance(self):
        try:
            balance = await self.exchange.fetch_balance()
            return float(balance['total'].get('USDT', 1000.0))
        except:
            return 1000.0

    async def get_history(self, symbol, interval='5m', limit=500):
        try:
            # Map Binance interval format
            # C# used KlineInterval.FiveMinutes
            klines = await self.exchange.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            # Ensure float types (logic parity with C# decimal)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df
        except Exception as e:
            print(f"[ERROR] Fetching history for {symbol}: {e}")
            return pd.DataFrame()

    async def get_position_information(self):
        try:
            positions = await self.exchange.fetch_positions()
            # C# returns list of positions with quantity
            return positions
        except:
            return []

    async def get_top_volume_symbols(self, limit=50):
        try:
            tickers = await self.exchange.fetch_tickers()
            usdt_tickers = [t for t in tickers.values() if t['symbol'].endswith('USDT')]
            # Sort by QuoteVolume (mirroring C# logic)
            sorted_tickers = sorted(usdt_tickers, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
            symbols = [t['symbol'] for t in sorted_tickers[:limit]]
            
            if symbols:
                return symbols
        except Exception as e:
            print(f"[ERROR] Fetching top symbols: {e}")

        # Static Fallback (100% parity with C# fix)
        return [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", 
            "PEPEUSDT", "SHIBUSDT", "WIFUSDT", "LINKUSDT", "AVAXUSDT", "NEARUSDT"
        ]

    def calculate_atr(self, df, period=14):
        if len(df) <= period:
            return 0.0
            
        # Parity with C# ATR calculation logic
        high = df['high']
        low = df['low']
        prev_close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return float(tr.tail(period).mean())
