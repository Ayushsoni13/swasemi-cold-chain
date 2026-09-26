from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(
    settings.sync_database_url,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def ensure_schema_up_to_date():
    """Ensure all tables and missing columns exist in SQLite database."""
    Base.metadata.create_all(bind=engine)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if "shipments" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("shipments")]
            cols_to_add = [
                ("origin_lat", "FLOAT"),
                ("origin_lng", "FLOAT"),
                ("target_lat", "FLOAT"),
                ("target_lng", "FLOAT"),
                ("route_name", "VARCHAR(255)"),
            ]
            with engine.connect() as conn:
                for col_name, col_type in cols_to_add:
                    if col_name not in columns:
                        conn.execute(text(f"ALTER TABLE shipments ADD COLUMN {col_name} {col_type}"))
                conn.commit()
    except Exception as e:
        print(f"Warning during DB schema sync: {e}")

# Run schema sync on module import
ensure_schema_up_to_date()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

