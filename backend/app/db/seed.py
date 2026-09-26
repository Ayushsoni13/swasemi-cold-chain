import sys
import logging
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, Base, engine
from app.models.organization import Organization
from app.models.user import User
from app.models.tracker import Tracker
from app.models.enums import RoleEnum, TrackerStatusEnum
from app.core.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SeedData")

# Demo Credentials
SUPER_ADMIN_EMAIL = "admin@swasemi.demo"
SUPER_ADMIN_PASSWORD = "DemoAdmin123!"

USER_A_EMAIL = "usera@swasemi.demo"
USER_A_PASSWORD = "DemoUser123!"

USER_B_EMAIL = "userb@swasemi.demo"
USER_B_PASSWORD = "DemoUser123!"

ORG_A_ID = "org-pharma-a"
ORG_B_ID = "org-biocold-b"

def seed_data(db: Session):
    logger.info("Seeding SWASEMI Cold-Chain Monitoring Platform database...")

    # 1. Organizations
    org_a = db.query(Organization).filter(Organization.id == ORG_A_ID).first()
    if not org_a:
        org_a = Organization(id=ORG_A_ID, name="PharmaCorp Global")
        db.add(org_a)
        logger.info(f"Created Organization A: {org_a.name} ({org_a.id})")

    org_b = db.query(Organization).filter(Organization.id == ORG_B_ID).first()
    if not org_b:
        org_b = Organization(id=ORG_B_ID, name="BioCold Logistics")
        db.add(org_b)
        logger.info(f"Created Organization B: {org_b.name} ({org_b.id})")

    db.commit()

    # 2. Users
    # Super Admin (organization_id = None)
    admin_user = db.query(User).filter(User.email == SUPER_ADMIN_EMAIL).first()
    if not admin_user:
        admin_user = User(
            id="user-super-admin",
            organization_id=None,
            email=SUPER_ADMIN_EMAIL,
            password_hash=hash_password(SUPER_ADMIN_PASSWORD),
            role=RoleEnum.SUPER_ADMIN
        )
        db.add(admin_user)
        logger.info(f"Created Super Admin user: {SUPER_ADMIN_EMAIL}")

    # User A (Organization A)
    user_a = db.query(User).filter(User.email == USER_A_EMAIL).first()
    if not user_a:
        user_a = User(
            id="user-org-a",
            organization_id=ORG_A_ID,
            email=USER_A_EMAIL,
            password_hash=hash_password(USER_A_PASSWORD),
            role=RoleEnum.USER
        )
        db.add(user_a)
        logger.info(f"Created User A: {USER_A_EMAIL} (Org: {ORG_A_ID})")

    # User B (Organization B)
    user_b = db.query(User).filter(User.email == USER_B_EMAIL).first()
    if not user_b:
        user_b = User(
            id="user-org-b",
            organization_id=ORG_B_ID,
            email=USER_B_EMAIL,
            password_hash=hash_password(USER_B_PASSWORD),
            role=RoleEnum.USER
        )
        db.add(user_b)
        logger.info(f"Created User B: {USER_B_EMAIL} (Org: {ORG_B_ID})")

    db.commit()

    # 3. Trackers (At least 3 moving trackers)
    trackers_data = [
        {"id": "TRK-001", "org_id": ORG_A_ID, "name": "Refrigerated Van A", "topic": "swasemi/telemetry/TRK-001"},
        {"id": "TRK-002", "org_id": ORG_B_ID, "name": "Cold Truck B", "topic": "swasemi/telemetry/TRK-002"},
        {"id": "TRK-003", "org_id": ORG_A_ID, "name": "Pharma Express C", "topic": "swasemi/telemetry/TRK-003"},
    ]

    for trk_info in trackers_data:
        tracker = db.query(Tracker).filter(Tracker.id == trk_info["id"]).first()
        if not tracker:
            tracker = Tracker(
                id=trk_info["id"],
                organization_id=trk_info["org_id"],
                name=trk_info["name"],
                mqtt_topic=trk_info["topic"],
                status=TrackerStatusEnum.ACTIVE.value
            )
            db.add(tracker)
            logger.info(f"Created Tracker: {tracker.id} - {tracker.name} (Org: {tracker.organization_id})")

    db.commit()
    logger.info("Database seeding successfully completed!")

def main():
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()

if __name__ == "__main__":
    main()
