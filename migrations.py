"""Idempotent, additive schema migrations for the shared MySQL database."""

MIGRATION_ID = "2026_10_20_admin_otp_and_replies"


def _table_exists(db, table_name):
    row = db.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = %s",
        (table_name,),
    ).fetchone()
    return bool(row)


def _column_exists(db, table_name, column_name):
    row = db.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s",
        (table_name, column_name),
    ).fetchone()
    return bool(row)


def _migration_is_recorded(db):
    row = db.execute(
        "SELECT 1 FROM schema_migrations WHERE version = %s",
        (MIGRATION_ID,),
    ).fetchone()
    return bool(row)


def apply_migrations(db):
    """Apply only missing additive changes; existing application data is untouched."""
    migration_recorded = (
        _table_exists(db, "schema_migrations")
        and _migration_is_recorded(db)
        and _table_exists(db, "contact_message_replies")
        and _column_exists(db, "feedback", "status")
    )
    if migration_recorded:
        return False

    db.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version VARCHAR(100) NOT NULL PRIMARY KEY, "
        "applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
        ") ENGINE=InnoDB"
    )
    migration_recorded = _migration_is_recorded(db)

    if not _column_exists(db, "feedback", "status"):
        db.execute(
            "ALTER TABLE feedback ADD COLUMN status "
            "ENUM('new','reviewed','resolved') NOT NULL DEFAULT 'new'"
        )

    db.execute(
        "CREATE TABLE IF NOT EXISTS contact_message_replies ("
        "id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, "
        "contact_message_id BIGINT UNSIGNED NOT NULL, "
        "admin_username VARCHAR(100) NOT NULL, "
        "recipient_email VARCHAR(255) NOT NULL, "
        "subject VARCHAR(255) NOT NULL, "
        "body TEXT NOT NULL, "
        "status ENUM('pending','sent','failed') NOT NULL DEFAULT 'pending', "
        "provider_message_id VARCHAR(255) NULL, "
        "error_message VARCHAR(255) NULL, "
        "idempotency_key CHAR(64) NOT NULL UNIQUE, "
        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
        "sent_at DATETIME NULL, "
        "CONSTRAINT fk_reply_message FOREIGN KEY (contact_message_id) "
        "REFERENCES contact_messages(id) ON DELETE RESTRICT, "
        "INDEX idx_reply_message_created (contact_message_id, created_at), "
        "INDEX idx_reply_status_created (status, created_at)"
        ") ENGINE=InnoDB"
    )
    if not migration_recorded:
        db.execute(
            "INSERT INTO schema_migrations (version) VALUES (%s)",
            (MIGRATION_ID,),
        )
    db.commit()
    return not migration_recorded
