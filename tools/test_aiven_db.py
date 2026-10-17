"""Read-only verification for the project's Aiven MySQL database."""
import os
import re
import sys
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT if (PROJECT_ROOT / "app.py").is_file() else PROJECT_ROOT / "what-next career guidance stream"
for env_path in (PROJECT_ROOT / ".env", APP_DIR / ".env"):
    load_dotenv(env_path, override=False)

EXPECTED_TABLES = (
    "users",
    "admins",
    "questions",
    "question_options",
    "user_responses",
    "quiz_results",
    "career_recommendations",
    "feedback",
    "contact_messages",
)


def required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def connection_config():
    ssl_mode = required_env("MYSQL_SSL_MODE").upper()
    if ssl_mode not in {"REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"}:
        raise ValueError("MYSQL_SSL_MODE must be REQUIRED, VERIFY_CA, or VERIFY_IDENTITY")

    host = required_env("MYSQL_HOST")
    port_value = required_env("MYSQL_PORT")
    if host.startswith("actual-") or port_value.startswith("actual-"):
        raise RuntimeError(
            "Replace placeholder MYSQL_HOST and MYSQL_PORT values in .env with the Aiven values"
        )
    try:
        port = int(port_value)
    except ValueError as error:
        raise RuntimeError("MYSQL_PORT must be the numeric Aiven port") from error

    config = {
        "host": host,
        "port": port,
        "user": required_env("MYSQL_USER"),
        "password": required_env("MYSQL_PASSWORD"),
        "database": required_env("MYSQL_DATABASE"),
        "ssl_disabled": False,
        "ssl_verify_cert": ssl_mode in {"VERIFY_CA", "VERIFY_IDENTITY"},
        "ssl_verify_identity": ssl_mode == "VERIFY_IDENTITY",
    }
    ssl_ca = os.environ.get("MYSQL_SSL_CA")
    if ssl_ca:
        ca_path = Path(ssl_ca)
        config["ssl_ca"] = str(ca_path if ca_path.is_absolute() else APP_DIR / ca_path)
    return config


def quote_identifier(identifier):
    return "`" + identifier.replace("`", "``") + "`"


def safe_error_message(error):
    message = str(error)
    password = os.environ.get("MYSQL_PASSWORD")
    if password:
        message = message.replace(password, "<redacted>")
    return re.sub(r"(password\s*[=:]\s*)[^\s,;]+", r"\1<redacted>", message, flags=re.IGNORECASE)


def main():
    connection = None
    print("AIVEN DATABASE CHECK")
    try:
        connection = mysql.connector.connect(**connection_config())
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        database_name = cursor.fetchone()[0]
        cursor.execute("SHOW TABLES")
        table_names = [row[0] for row in cursor.fetchall()]
        table_set = set(table_names)

        print("Connection: SUCCESS")
        print(f"Database: {database_name}")
        print("Aiven MySQL connection successful")
        print("Tables found:")
        for table_name in table_names:
            print(f"- {table_name}")

        print("Record counts:")
        for table_name in EXPECTED_TABLES:
            if table_name not in table_set:
                print(f"- {table_name}: NOT FOUND")
                continue
            cursor.execute(f"SELECT COUNT(*) FROM {quote_identifier(table_name)}")
            count = cursor.fetchone()[0]
            print(f"- {table_name}: {count}")
            cursor.execute(f"SELECT * FROM {quote_identifier(table_name)} LIMIT 1")
            sample = cursor.fetchone()
            print(f"  sample SELECT: {'DATA FOUND' if sample is not None else 'NO ROWS'}")

        return 0
    except (mysql.connector.Error, KeyError, OSError, ValueError, RuntimeError) as error:
        print("Connection: FAILED")
        print(f"Error: {safe_error_message(error)}")
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    sys.exit(main())
