import asyncio
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from termcolor import colored

# Import ported modules
from market_data import MarketDataManager
from smc_analyzer import SMCAnalyzer
from risk_manager import RiskManager
from trade_executor import TradeExecutor
from history_manager import HistoryManager
from telegram_logger import TelegramLogger

# Load credentials
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY", "your_api_key")
API_SECRET = os.getenv("BINANCE_API_SECRET", "your_api_secret")
TELEGRAM_TOKEN = "8263621494:AAHQEhN5wxDRK9RxQ7VaCDUCqV16N-XA2YE"
TELEGRAM_CHAT_ID = "6482879291"

# Global Managers
market = MarketDataManager(API_KEY, API_SECRET)
history = HistoryManager()
executor = TradeExecutor(market.exchange, history)
risk = RiskManager()
telegram = TelegramLogger(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

# Constants (Parity with C#)
MAX_SLOTS = 3
SCAN_DELAY = 10  # Seconds

async def scan_single_symbol(symbol):
    try:
        # A. Multi-TF Bias (1H Parity)
        df_1h = await market.get_history(symbol, interval='1h', limit=50)
        if df_1h.empty: return

        # SMC Analysis for 1H Bias
        bias_analyzer = SMCAnalyzer()
        bias_analyzer.analyze(df_1h)
        last_1h = df_1h.iloc[-1]
        
        # Bullish if Price > EMA (Simplified trend) or recent BOS_BULL
        is_bullish_bias = last_1h['close'] > df_1h['close'].rolling(20).mean().iloc[-1]
        
        # B. Entry TF (5m Parity)
        df_5m = await market.get_history(symbol, interval='5m', limit=100)
        if df_5m.empty: return

        analyzer = SMCAnalyzer()
        analyzer.analyze(df_5m)
        current = df_5m.iloc[-1]
        atr = market.calculate_atr(df_5m)

        # C. Signal Logic (SMC Pro Ultra Parity)
        # Bullish: Bias UP + CHoCH + IDM + OB/FVG Alignment + Discount Zone
        bullish_signal = is_bullish_bias and analyzer.has_choch and analyzer.has_idm and \
                        (analyzer.is_inside_ob(current['close'], True) or analyzer.is_price_in_fvg(current['close'], True)) and \
                        analyzer.is_in_discount(current['close'], True)

        # Bearish: Bias DOWN + CHoCH + IDM + OB/FVG Alignment + Premium Zone
        bearish_signal = (not is_bullish_bias) and analyzer.has_choch and analyzer.has_idm and \
                         (analyzer.is_inside_ob(current['close'], False) or analyzer.is_price_in_fvg(current['close'], False)) and \
                         (not analyzer.is_in_discount(current['close'], False))

        if bullish_signal or bearish_signal:
            # D. Slot Management
            total_open = await executor.get_total_open_positions()
            if total_open >= MAX_SLOTS:
                print(f"[SLOTS FULL] Skipping {symbol} signal.")
                return

            # E. Confirm Candle Close (RiskManager Parity)
            if not risk.should_confirm_entry(current, bullish_signal):
                print(f"[WAITING] {symbol} signal found, but waiting for candle confirmation.")
                return

            # F. Execute Trade
            capital = await market.get_balance()
            trade_data = risk.calculate_trade(current['close'], capital, bearish_signal, atr)

            await executor.execute_trade(
                symbol, bearish_signal, trade_data['quantity'], 
                trade_data['stop_loss'], trade_data['take_profit']
            )

            # G. Telegram Alert
            alert_msg = f"🚀 *SMC SIGNAL: {symbol}*\n" \
                        f"Side: {'SHORT' if bearish_signal else 'LONG'}\n" \
                        f"Price: {current['close']}\n" \
                        f"SL: {trade_data['stop_loss']:.4f}\n" \
                        f"TP: {trade_data['take_profit']:.4f}\n" \
                        f"Reason: CHoCH + IDM + Zone Alignment"
            await telegram.log_async(alert_msg)

    except Exception as e:
        print(f"[SCAN ERROR] {symbol}: {e}")

async def sync_closed_trades():
    """Syncs SQLite with actual Binance status (Parity with Program.cs)"""
    open_in_db = history.get_open_trades()
    if not open_in_db: return

    for trade in open_in_db:
        has_pos = await executor.has_open_position(trade['symbol'])
        if not has_pos:
            # Trade closed on Binance (SL/TP hit)
            # Calculate P&L (simplified for parity)
            df = await market.get_history(trade['symbol'], limit=2)
            exit_price = df.iloc[-1]['close']
            
            pnl = (exit_price - trade['entry_price']) / trade['entry_price'] * 100
            if trade['side'] == "SHORT": pnl *= -1
            
            history.close_trade(trade['id'], exit_price, pnl)
            
            msg = f"✅ *TRADE CLOSED: {trade['symbol']}*\n" \
                  f"Side: {trade['side']}\n" \
                  f"Exit: {exit_price}\n" \
                  f"PnL: {pnl:.2f}%"
            await telegram.log_async(msg)

async def run_cycle():
    """Single execution cycle for Serverless/Cron deployment"""
    start_time = time.time()
    
    # 1. Dashboard Stats
    total_pnl, wins, losses = history.get_stats()
    stats_msg = (
        f"\n--- [ DASHBOARD ] {datetime.now().strftime('%H:%M:%S')} ---\n"
        f"LIFETIME P&L: {total_pnl:.2f}%\n"
        f"WINS: {wins} | LOSSES: {losses}\n"
        "------------------------------------------"
    )
    print(stats_msg)

    # 2. Sync Positions
    await sync_closed_trades()

    # 3. Parallel Scanning
    symbols = await market.get_top_volume_symbols(limit=30)
    print(f"Scanning {len(symbols)} high-volume symbols...")
    
    tasks = [scan_single_symbol(s) for s in symbols]
    await asyncio.gather(*tasks)

    elapsed = time.time() - start_time
    return f"{stats_msg}\nScanned {len(symbols)} symbols in {elapsed:.2f}s."

async def main():
    print(colored("==========================================", "yellow"))
    print(colored("   SMC PRO ULTRA (PYTHON VERSION)   ", "yellow", attrs=['bold']))
    print(colored("==========================================", "yellow"))

    while True:
        await run_cycle()
        await asyncio.sleep(SCAN_DELAY)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot Stop Requested.")
    finally:
        asyncio.run(market.close())
