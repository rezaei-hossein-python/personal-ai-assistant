from app.database.database import SessionLocal
from app.services.embedding_backfill_service import backfill_missing_chunk_embeddings


def main() -> int:
    db = SessionLocal()
    try:
        result = backfill_missing_chunk_embeddings(db)
    finally:
        db.close()

    print(f"scanned_count={result.scanned_count}")
    print(f"updated_count={result.updated_count}")
    print(f"skipped_count={result.skipped_count}")
    print(f"failed_count={result.failed_count}")

    return 1 if result.failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
