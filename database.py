from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import config

# Создаем движок БД
engine = create_engine(config.Config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    full_name = Column(String(200))
    balance = Column(Float, default=0.0)
    trial_used = Column(Boolean, default=False)  # Этот столбец был добавлен
    created_at = Column(DateTime, default=datetime.utcnow)
    
    payments = relationship("Payment", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    keys = relationship("VPNKey", back_populates="user")

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="RUB")
    payment_id = Column(String(100), unique=True)
    status = Column(String(20), default="pending")
    payment_method = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="payments")

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    tariff = Column(String(50))
    price = Column(Float)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="subscriptions")

class VPNKey(Base):
    __tablename__ = 'vpn_keys'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    key_id = Column(String(100))
    key = Column(Text)
    name = Column(String(100))
    data_limit = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="keys")

# Создаем таблицы
def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы базы данных созданы")
    print("   - users (с trial_used)")
    print("   - payments")
    print("   - subscriptions")
    print("   - vpn_keys")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Инициализируем БД при импорте
init_db()
