import sys
import os
import time
import logging
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Add parent directory to path so we can import shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db_models import Base, EA, Trade, AppConfig, AccountSnapshot, OpenPosition, get_engine, create_tables
from collector.config_vps import DATABASE_URL, MT5_PATHS as ENV_MT5_PATHS, LOG_LEVEL

# Setup Logging
logging.basicConfig(
    filename='collector.log',
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, LOG_LEVEL.upper()))
logging.getLogger().addHandler(console_handler)

def connect_mt5(path=None):
    """Initialize MT5 connection"""
    if not mt5.initialize(path=path) if path else mt5.initialize():
        logging.error(f"MT5 Initialize failed for path {path or 'default'}, error code = {mt5.last_error()}")
        return False
    
    # Ensure terminal is ready
    if not mt5.terminal_info():
        logging.error("Terminal info not available")
        return False
        
    logging.info(f"Connected to MT5 Terminal at {path}. Account: {mt5.account_info().login}")
    return True

def sync_trades(session, account_id):
    """
    Main logic:
    1. Get last trade time from DB.
    2. Fetch new trades from MT5 since that time.
    3. Insert into DB.
    """
    try:
        # 1. Get last known trade time from DB
        # 1. Get last known trade time from DB for this account
        last_trade_query = select(Trade.close_time).where(Trade.account_id == account_id).order_by(Trade.close_time.desc()).limit(1)
        result = session.execute(last_trade_query).scalar()
        
        if result:
            from_date = result
            # Add 1 second to avoid duplicate fetch of the last second
            from_date = from_date.replace(tzinfo=timezone.utc) 
            logging.info(f"Last trade in DB: {from_date}")
        else:
             # If DB empty, fetch last 3650 days (10 years)
            from_date = datetime.now(timezone.utc) - timedelta(days=3650)
            logging.info("DB empty. Fetching full history (10 years).")

        # 2. Fetch history from MT5
        # history_deals_get returns deals in UTC (usually) or Broker time. 
        # CAUTION: MT5 returns naive datetimes usually in Broker Time.
        # Ideally we should convert everything to UTC. For this POC we store as-is.
        deals = mt5.history_deals_get(from_date, datetime.now(timezone.utc))

        if deals is None:
            logging.info("No deals found or error fetching deals.")
            return

        if len(deals) == 0:
            logging.info("No new deals.")
            return

        logging.info(f"Found {len(deals)} new deals from MT5.")
        
        new_trades_count = 0
        
        for deal in deals:
            # Check if trade already exists (deduplication)
            exists = session.query(Trade).filter_by(ticket=deal.ticket).first()
            if exists:
                continue

            # Map MT5 Deal to DB Trade
            # Only record closed trades (entry out/inout) or balance ops if you want
            # Deal types: 0=BUY, 1=SELL, 2=BALANCE...
            # Entry: 0=IN, 1=OUT, 2=INOUT
            
            # Simple filer: We want entries that are OUT or INOUT (closing a position)
            # OR we just store everything and filter in SQL. Storing everything is safer.
            
            type_str = "UNKNOWN"
            if deal.type == mt5.DEAL_TYPE_BUY: type_str = "BUY"
            elif deal.type == mt5.DEAL_TYPE_SELL: type_str = "SELL"
            elif deal.type == mt5.DEAL_TYPE_BALANCE: type_str = "BALANCE"
            
            # Convert timestamp to python datetime
            dt = datetime.fromtimestamp(deal.time, tz=timezone.utc)

            trade = Trade(
                account_id=account_id,
                ticket=deal.ticket,
                magic_number=deal.magic,
                symbol=deal.symbol,
                type=type_str,
                volume=deal.volume,
                open_price=deal.price, # For a deal, 'price' is execution price
                close_price=0.0, # Deal doesn't have open/close, it IS the close or open. 
                                 # Simplification: we store deals as atomic events. 
                                 # Reconstructing full "Trades" (Open+Close) requires matching IN and OUT deals.
                                 # For V1 POC, we just store the deals.
                open_time=dt,
                close_time=dt, # Using same time for simplicity in Deal model
                profit=deal.profit,
                commission=deal.commission,
                swap=deal.swap,
                comment=deal.comment
            )
            
            # Debug log for first trade
            if new_trades_count == 0:
                logging.info(f"Inserting Trade with Account ID: {trade.account_id}")

            session.add(trade)
            
            # Auto-Register EA if new magic number AND account_id
            ea = session.query(EA).filter_by(magic_number=deal.magic, account_id=account_id).first()
            if not ea:
                new_ea = EA(magic_number=deal.magic, account_id=account_id, name=f"EA_{deal.magic}", description=f"Auto-discovered on {account_id}")
                session.add(new_ea)
                logging.info(f"Discovered new EA: {deal.magic} on Account {account_id}")

            new_trades_count += 1

        session.commit()
        if new_trades_count > 0:
            logging.info(f"Successfully synced {new_trades_count} new trades.")
        
    except Exception as e:
        logging.error(f"Error in sync loop: {e}")
        session.rollback()

def sync_account_snapshot(session, account_id):
    """Capture Equity, Balance, Margin (TimeSeries)"""
    try:
        info = mt5.account_info()
        if not info:
            return

        snapshot = AccountSnapshot(
            account_id=account_id,
            timestamp=datetime.now(timezone.utc),
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            free_margin=info.margin_free,
            margin_level=info.margin_level,
            open_pnl=info.profit
        )
        session.add(snapshot)
        session.commit()
    except Exception as e:
        logging.error(f"Error snapshotting account {account_id}: {e}")
        session.rollback()

def sync_open_positions(session, account_id):
    """Sync Open Positions (Full Replace for Current State)"""
    try:
        positions = mt5.positions_get()
        if positions is None: 
            return

        # 1. Clear existing open positions for this account
        session.query(OpenPosition).filter_by(account_id=account_id).delete()
        
        # 2. Insert current
        for pos in positions:
            type_str = "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
            
            db_pos = OpenPosition(
                ticket=pos.ticket,
                account_id=account_id,
                symbol=pos.symbol,
                magic_number=pos.magic,
                type=type_str,
                volume=pos.volume,
                open_price=pos.price_open,
                current_price=pos.price_current,
                sl=pos.sl,
                tp=pos.tp,
                profit=pos.profit,
                swap=pos.swap,
                comment=pos.comment
            )
            session.add(db_pos)
        
        session.commit()
        if len(positions) > 0:
            logging.info(f"Synced {len(positions)} open positions.")
            
    except Exception as e:
        logging.error(f"Error syncing positions for {account_id}: {e}")
        session.rollback()

def get_config_paths(session):
    """Fetch MT5 paths from DB, fallback to ENV"""
    try:
        config = session.query(AppConfig).filter_by(key="mt5_paths").first()
        if config and config.value:
            paths = [p.strip() for p in config.value.split(";") if p.strip()]
            if paths:
                return paths
    except Exception as e:
        logging.error(f"Error fetching config from DB: {e}")
    
    return ENV_MT5_PATHS

def main():
    logging.info("Starting Collector Service...")
    
    # 1. Connect to DB
    engine = get_engine(DATABASE_URL)
    create_tables(engine) # Ensure tables exist
    Session = sessionmaker(bind=engine)
    session = Session()
    logging.info("Database connected.")

    # 3. Main Loop
    try:
        while True:
            # Refresh Config every cycle
            current_paths = get_config_paths(session)
            
            if not current_paths:
                logging.warning("No MT5_PATH configured in DB or ENV. Trying default.")
                current_paths = [None]
            
            logging.info(f"Found {len(current_paths)} terminal(s) to sync.")

            for path in current_paths:
                try:
                    logging.info(f"--- Syncing Terminal: {path or 'Default'} ---")
                    if connect_mt5(path):
                        # Get Account ID
                        account_info = mt5.account_info()
                        if account_info:
                            account_id = int(account_info.login)
                            logging.info(f"Targeting Account ID: {account_id}")
                            sync_trades(session, account_id)
                            sync_account_snapshot(session, account_id)
                            sync_open_positions(session, account_id)
                        else:
                            logging.error("Failed to get account info")
                        
                        # Shutdown to release lock/context for next terminal
                        mt5.shutdown()
                    else:
                        logging.error(f"Failed to connect to {path}")
                except Exception as e:
                    logging.error(f"Error processing path {path}: {e}")
                    mt5.shutdown()
            
            logging.info("Cycle complete. Sleeping 60s...")
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Stopping Collector...")
        mt5.shutdown()
        sys.exit(0)

if __name__ == "__main__":
    main()
