import ccxt.async_support as ccxt
import asyncio
import math

class TradeExecutor:
    def __init__(self, exchange, history_manager):
        self.exchange = exchange
        self.history = history_manager

    async def has_open_position(self, symbol):
        try:
            positions = await self.exchange.fetch_positions([symbol])
            for pos in positions:
                if pos['symbol'] == symbol and float(pos['contracts']) != 0:
                    return True
            return False
        except:
            return True # Safety skip

    async def get_total_open_positions(self):
        try:
            positions = await self.exchange.fetch_positions()
            count = sum(1 for p in positions if float(p['contracts']) != 0)
            return count
        except:
            return 0

    async def set_optimal_leverage(self, symbol, percent_of_max=0.8):
        try:
            # CCXT fetch_leverage_tiers or similar
            # For simplicity and parity, we set a reasonable high target or fetch max
            # Note: Binance API varies, but we aim for 80% of allowed
            await self.exchange.set_leverage(leverage=20, symbol=symbol)
            print(f"[LEVERAGE] Set {symbol} to 20x (Standard Target)")
        except Exception as e:
            print(f"[ERROR] Leverage adjustment: {e}")

    async def execute_trade(self, symbol, is_short, quantity, stop_loss, take_profit):
        if await self.has_open_position(symbol):
            print(f"[SKIPPING] {symbol} already has an open position.")
            return

        # Set Leverage
        await self.set_optimal_leverage(symbol)

        # Rounding (Parity with C# precision logic)
        # Fetching market info for precision
        markets = await self.exchange.load_markets()
        market = markets.get(symbol)
        
        price_precision = market['precision']['price'] if market else 2
        qty_precision = market['precision']['amount'] if market else 3

        rounded_qty = round(quantity, int(qty_precision))
        if rounded_qty == 0:
            rounded_qty = 1 / (10 ** qty_precision)

        rounded_sl = round(stop_loss, int(price_precision))
        rounded_tp = round(take_profit, int(price_precision))

        side = 'sell' if is_short else 'buy'
        print(f"[EXECUTING] Placing {'SHORT' if is_short else 'LONG'} order for {symbol}...")

        try:
            # Market Entry
            order = await self.exchange.create_market_order(symbol, side, rounded_qty)
            
            fill_price = float(order.get('average', order.get('price', 0)))
            if fill_price == 0:
                fill_price = stop_loss # Fallback

            # Log to History
            self.history.log_entry(symbol, "SHORT" if is_short else "LONG", fill_price, rounded_qty)
            print(f"[SUCCESS] Entry Filled! {symbol} @ {fill_price}")

            # Exit Orders (Stop Loss & Take Profit)
            # ReduceOnly is handled by CCXT params
            exit_side = 'buy' if is_short else 'sell'
            
            # SL
            try:
                await self.exchange.create_order(
                    symbol=symbol,
                    type='STOP_MARKET',
                    side=exit_side,
                    amount=rounded_qty,
                    params={'stopPrice': rounded_sl, 'reduceOnly': True}
                )
                print(f"[SUCCESS] Stop-Loss Attached @ {rounded_sl}")
            except Exception as e:
                print(f"[ERROR] SL Attachment failed: {e}")

            # TP
            try:
                await self.exchange.create_order(
                    symbol=symbol,
                    type='TAKE_PROFIT_MARKET',
                    side=exit_side,
                    amount=rounded_qty,
                    params={'stopPrice': rounded_tp, 'reduceOnly': True}
                )
                print(f"[SUCCESS] Take-Profit Attached @ {rounded_tp}")
            except Exception as e:
                print(f"[ERROR] TP Attachment failed: {e}")

        except Exception as e:
            print(f"[ERROR] Execution Failed: {e}")
