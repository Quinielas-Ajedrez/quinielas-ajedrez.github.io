#!/usr/bin/env python3
"""
Import a tournament from YAML into the database.
Usage: python -m backend.import_tournament <path_to.yaml>
       python -m backend.import_tournament --init  # create DB and exit
"""

import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal, init_db
from backend.repository import save_tournament
from backend.yaml_parser import parse_tournament_yaml


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m backend.import_tournament <path_to.yaml>")
        print("       python -m backend.import_tournament --init  # init DB only")
        sys.exit(1)

    init_db()
    print("Database initialized.")

    if sys.argv[1] == "--init":
        return

    yaml_path = Path(sys.argv[1])
    if not yaml_path.exists():
        print(f"Error: File not found: {yaml_path}")
        sys.exit(1)

    tournament = parse_tournament_yaml(yaml_path)
    print(f"Parsed tournament: {tournament.name} with {len(tournament.rounds)} rounds")

    with SessionLocal() as session:
        saved = save_tournament(session, tournament)
        print(f"Saved tournament with id={saved.id}")


if __name__ == "__main__":
    main()
