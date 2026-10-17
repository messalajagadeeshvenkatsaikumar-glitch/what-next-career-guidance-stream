"""Read-only connectivity and record-count comparison for two Aiven MySQL services."""
import os
import re
import socket
import sys
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT if (PROJECT_ROOT / "app.py").is_file() else PROJECT_ROOT / "what-next career guidance stream"
for env_path in (PROJECT_ROOT / ".env", APP_DIR / ".env"):
    load_dotenv(env_path, override=False)

PROJECT_TABLES = (
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


def required_env(prefix, name):
    value = os.environ.get(f"{prefix}_{name}")
    if not value:
        raise RuntimeError(f"Missing required environment variable: {prefix}_{name}")
    return value


def missing_variables():
    names = (
        "SOURCE_AIVEN_HOST", "SOURCE_AIVEN_PORT", "SOURCE_AIVEN_USER",
        "SOURCE_AIVEN_PASSWORD", "SOURCE_AIVEN_DATABASE",
        "DEST_AIVEN_HOST", "DEST_AIVEN_PORT", "DEST_AIVEN_USER",
        "DEST_AIVEN_PASSWORD", "DEST_AIVEN_DATABASE",
    )
    return [name for name in names if not os.environ.get(name)]


def masked_host(host):
    parts = host.split(".")
    if len(parts) == 1:
        return "<masked>"
    return "..." + "." + ".".join(parts[-2:])


def connection_config(prefix):
    host = required_env(prefix, "HOST")
    port_text = required_env(prefix, "PORT")
    try:
        port = int(port_text)
    except ValueError as error:
        raise RuntimeError(f"{prefix}_PORT must be a numeric port") from error
    if not 1 <= port <= 65535:
        raise RuntimeError(f"{prefix}_PORT must be between 1 and 65535")

    return {
        "host": host,
        "port": port,
        "user": required_env(prefix, "USER"),
        "password": required_env(prefix, "PASSWORD"),
        "database": required_env(prefix, "DATABASE"),
        "connection_timeout": 10,
        "ssl_disabled": False,
    }


def quote_identifier(identifier):
    return "`" + identifier.replace("`", "``") + "`"


def safe_error_message(error):
    message = str(error)
    for name in ("SOURCE_AIVEN_PASSWORD", "DEST_AIVEN_PASSWORD"):
        password = os.environ.get(name)
        if password:
            message = message.replace(password, "<redacted>")
    return re.sub(r"(password\s*[=:]\s*)[^\s,;]+", r"\1<redacted>", message, flags=re.IGNORECASE)


def classify_error(error):
    code = getattr(error, "errno", None)
    message = str(error).lower()
    if code == 1045 or "access denied" in message:
        return "authentication failure"
    if code in {2003, 2005} or "getaddrinfo" in message or "unknown host" in message:
        return "wrong hostname"
    if code in {2003, 2004} and ("port" in message or "timed out" in message):
        return "wrong port or connection timeout"
    if "ssl" in message or "tls" in message or "certificate" in message:
        return "SSL/TLS failure"
    if code in {1049} or "unknown database" in message:
        return "database does not exist"
    if "timeout" in message or "timed out" in message:
        return "connection timeout"
    return "connection error"


def same_service(source_config, destination_config):
    source_host = source_config["host"].rstrip(".").lower()
    destination_host = destination_config["host"].rstrip(".").lower()
    return source_host == destination_host and source_config["port"] == destination_config["port"]


def inspect_database(prefix):
    config = connection_config(prefix)
    result = {
        "prefix": prefix,
        "host": masked_host(config["host"]),
        "database": config["database"],
        "success": False,
        "tables": [],
        "counts": {},
        "error": None,
    }
    connection = None
    try:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.execute("SELECT DATABASE()")
        result["database"] = cursor.fetchone()[0]
        cursor.execute("SHOW TABLES")
        result["tables"] = [row[0] for row in cursor.fetchall()]
        existing = set(result["tables"])
        for table_name in PROJECT_TABLES:
            if table_name in existing:
                cursor.execute(f"SELECT COUNT(*) FROM {quote_identifier(table_name)}")
                result["counts"][table_name] = cursor.fetchone()[0]
        result["success"] = True
    except (mysql.connector.Error, KeyError, OSError, ValueError, RuntimeError) as error:
        result["error"] = f"{classify_error(error)}: {safe_error_message(error)}"
    finally:
        if connection is not None:
            connection.close()
    return result


def print_section(label, result):
    status = "SUCCESS" if result["success"] else "FAILED"
    print(f"{label}:")
    print(f"Connection: {status}")
    print(f"Host: {result['host']}")
    print(f"Database: {result['database']}")
    print(f"Tables found: {len(result['tables'])}")
    if result["tables"]:
        print("Tables: " + ", ".join(result["tables"]))
    if result["error"]:
        print(f"Error: {result['error']}")


def main():
    print("AIVEN-TO-AIVEN CONNECTION TEST")
    missing = missing_variables()
    if missing:
        print("Configuration: FAILED")
        print("Missing environment variables: " + ", ".join(missing))
        return 1
    try:
        source_config = connection_config("SOURCE_AIVEN")
        destination_config = connection_config("DEST_AIVEN")
    except (KeyError, ValueError, RuntimeError) as error:
        print(f"Configuration: FAILED - {safe_error_message(error)}")
        return 1

    if same_service(source_config, destination_config):
        print("ERROR: Source and destination are the same Aiven service.")
        print("Do not attempt migration.")
        return 1

    source = inspect_database("SOURCE_AIVEN")
    destination = inspect_database("DEST_AIVEN")
    print_section("SOURCE", source)
    print_section("DESTINATION", destination)

    if source["success"] and destination["success"]:
        common_tables = sorted(set(source["counts"]) & set(destination["counts"]))
        print("\nTable | Source rows | Destination rows")
        print("--- | ---: | ---:")
        for table_name in common_tables:
            print(f"{table_name} | {source['counts'][table_name]} | {destination['counts'][table_name]}")
        print("\nSource and destination are different Aiven services.")
        print("Aiven-to-Aiven connectivity test completed.")
        return 0

    print("\nAiven-to-Aiven connectivity test failed; migration must not be attempted.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
