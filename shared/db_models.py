from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

class EA(Base):
    """Registry of Expert Advisors"""
    __tablename__ = 'eas'

    magic_number = Column(BigInteger, primary_key=True)
    account_id = Column(BigInteger, primary_key=True) # Composite Key: Strategy on specific account
    name = Column(String, nullable=False) # e.g. "Scalper_v1"
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AppConfig(Base):
    """Global Application Configuration"""
    __tablename__ = 'app_config'
    
    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Trade(Base):
    """Historical Trade Data"""
    __tablename__ = 'trades'

    ticket = Column(BigInteger, primary_key=True)
    account_id = Column(BigInteger, index=True) # MT5 Login ID
    magic_number = Column(BigInteger, index=True) # Foreign Key logically
    symbol = Column(String, index=True)
    type = Column(String) # "BUY", "SELL"
    volume = Column(Float)
    open_price = Column(Float)
    close_price = Column(Float)
    open_time = Column(DateTime)
    close_time = Column(DateTime, index=True)
    profit = Column(Float)
    commission = Column(Float)
    swap = Column(Float)
    comment = Column(String)

class AccountSnapshot(Base):
    """TimeSeries data for Account Health (Equity, Margin, etc.)"""
    __tablename__ = 'account_snapshots'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    account_id = Column(BigInteger, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    balance = Column(Float)
    equity = Column(Float)
    margin = Column(Float)
    free_margin = Column(Float)
    margin_level = Column(Float)
    open_pnl = Column(Float)
    
    # Flexible field for future metrics (stored as JSON string)
    extra_data = Column(String, nullable=True)

class AccountAlias(Base):
    __tablename__ = 'account_aliases'
    account_id = Column(String, primary_key=True)
    alias = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OpenPosition(Base):
    """Live Views of currently open trades"""
    __tablename__ = 'open_positions'

    ticket = Column(BigInteger, primary_key=True)
    account_id = Column(BigInteger, index=True)
    symbol = Column(String)
    magic_number = Column(BigInteger)
    type = Column(String) # "BUY", "SELL"
    volume = Column(Float)
    open_price = Column(Float)
    current_price = Column(Float)
    sl = Column(Float)
    tp = Column(Float)
    profit = Column(Float)
    swap = Column(Float)
    comment = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def get_engine(db_url: str):
    return create_engine(db_url)

def create_tables(engine):
    # WARNING: Dropping all tables to handle schema changes during dev
    # Base.metadata.drop_all(engine) # Uncomment if you want to force reset
    pass # Managed manually or via drop_all in init_db
