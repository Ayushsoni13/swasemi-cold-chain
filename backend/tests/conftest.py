import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Use dedicated test database for pytest to isolate from background server/simulator
os.environ["DATABASE_URL"] = "sqlite:///./test_swasemi.db"

# Import all models to register with Base.metadata
from app.models import Organization, User, Tracker, Shipment, TelemetryReading, Alert
from app.db.session import engine, Base

# Recreate all tables in test database to ensure fresh schema
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

