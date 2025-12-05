# seed_departments.py
"""
Standalone script to seed initial department data into the PostgreSQL database.
This must be run after the application context (app) and database tables (db) 
have been successfully created (using Flask-Migrate).
"""

from models import db, Department
from app import create_app
import logging
import sys

logger = logging.getLogger(__name__)

# CRITICAL FIX: This list MUST EXACTLY match the DEPARTMENTS list in reasoning/kg_gnn.py
DEPARTMENTS_TO_SEED = [
    "Waste Management",
    "Construction",
    "Municipality",
    "Roads",
    "Electricity",
    "Water",
    "Ward Office"
]

def seed_departments():
    # Application setup
    try:
        app = create_app()
    except Exception as e:
        logger.error(f"Failed to create application context: {e}")
        sys.exit(1)
        
    with app.app_context():
        print("Starting department seeding...")
        
        # Check and add missing departments
        for name in DEPARTMENTS_TO_SEED:
            # Check for existing department
            if not Department.query.filter_by(name=name).first():
                try:
                    db.session.add(Department(name=name))
                    logger.info(f"Adding department: {name}")
                except Exception as e:
                    # Log error but attempt to continue for other departments
                    logger.error(f"Failed to add department {name}: {e}")
                    db.session.rollback()
        
        try:
            # Commit all additions in one transaction
            db.session.commit()
            print("Departments added/checked successfully in the database.")
        except Exception as e:
            logger.error(f"Failed to commit department seeding changes: {e}")
            db.session.rollback()
            print("Database transaction failed and was rolled back.")


if __name__ == '__main__':
    seed_departments()