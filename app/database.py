from databases import Database
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime
import datetime

DATABASE_URL = "sqlite:///./payments.db"

database = Database(DATABASE_URL)
metadata = MetaData()

payments = Table(
    "payments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", String, unique=True, index=True),
    Column("customer_email", String),
    Column("amount", Integer),
    Column("currency", String),
    Column("created_at", DateTime, default=datetime.datetime.utcnow)
)

engine = create_engine(DATABASE_URL)
metadata.create_all(engine)