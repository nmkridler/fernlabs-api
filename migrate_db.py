#!/usr/bin/env python3
"""
Database migration script for FernLabs API
"""

from sqlalchemy import create_engine, text
from fernlabs_api.settings import APISettings
from fernlabs_api.db import create_tables

settings = APISettings()


def migrate_database():
    """Run database migrations"""

    # Create engine
    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        # Check if prompt column exists
        result = conn.execute(
            text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'projects' AND column_name = 'prompt'
        """)
        )

        if not result.fetchone():
            print("Adding prompt column to projects table...")
            conn.execute(
                text("""
                ALTER TABLE projects
                ADD COLUMN prompt TEXT NOT NULL DEFAULT 'Default prompt'
            """)
            )
            print("Prompt column added successfully!")
        else:
            print("Prompt column already exists.")

        # Update status column default value if needed
        result = conn.execute(
            text("""
            SELECT column_default
            FROM information_schema.columns
            WHERE table_name = 'projects' AND column_name = 'status'
        """)
        )

        if result.fetchone():
            current_default = result.fetchone()[0]
            if current_default != "'loading'":
                print("Updating status column default value...")
                conn.execute(
                    text("""
                    ALTER TABLE projects
                    ALTER COLUMN status SET DEFAULT 'loading'
                """)
                )
                print("Status column default updated!")

        conn.commit()

    print("Database migration completed!")


if __name__ == "__main__":
    migrate_database()
