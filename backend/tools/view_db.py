import argparse
import json
import os
import sqlite3
from pathlib import Path


def default_db_path() -> Path:
    return Path(
        os.getenv(
            "NEKX_DB_PATH",
            str(Path(__file__).resolve().parents[2] / "data" / "nekx.db"),
        )
    )


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows]


def fetch_table_rows(conn: sqlite3.Connection, table: str, limit: int | None) -> list[dict]:
    sql = f"SELECT * FROM {quote_ident(table)}"
    if limit is not None:
        sql += " LIMIT ?"
        rows = conn.execute(sql, (limit,)).fetchall()
    else:
        rows = conn.execute(sql).fetchall()
    return [dict(row) for row in rows]


def print_table(conn: sqlite3.Connection, table: str, limit: int | None) -> None:
    rows = fetch_table_rows(conn, table, limit)

    print(f"\n=== {table} ({len(rows)} rows shown) ===")
    if not rows:
        print("(empty)")
        return

    for row in rows:
        print(row)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="View content from the local Nekx SQLite database.")
    parser.add_argument("--db-path", default=str(default_db_path()), help="Path to SQLite DB file")
    parser.add_argument(
        "--table",
        action="append",
        help="Table name to display (can be repeated). Defaults to all tables.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit rows per table (default: show all rows).",
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Print SQL dump (schema + data) using sqlite iterdump output.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print rows as JSON object keyed by table name.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    conn = sqlite3.connect(args.db_path)
    conn.row_factory = sqlite3.Row
    try:
        if args.dump and args.json:
            raise SystemExit("--dump and --json cannot be used together.")

        if args.dump:
            for line in conn.iterdump():
                print(line)
            return

        tables = args.table or list_tables(conn)
        if args.json:
            payload = {table: fetch_table_rows(conn, table, args.limit) for table in tables}
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        for table in tables:
            print_table(conn, table, args.limit)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
