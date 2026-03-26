from __future__ import annotations

from db import db_conn, fetch_all, init_db, log_event
from utils import utc_now_iso


def main() -> None:
    now = utc_now_iso()

    with db_conn() as conn:
        init_db(conn)

        rows = fetch_all(
            conn,
            """
            SELECT gp.id AS generated_post_id, gp.platform
            FROM generated_posts gp
            LEFT JOIN post_jobs pj ON pj.generated_post_id = gp.id
            WHERE pj.id IS NULL
            ORDER BY gp.id ASC
            """,
        )

        inserted = 0
        for r in rows:
            gp_id = int(r["generated_post_id"])
            platform = str(r["platform"])
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO post_jobs
                  (generated_post_id, platform, status, attempts, max_attempts,
                   last_error, locked_at, completed_at, created_at, updated_at)
                VALUES (?, ?, 'pending', 0, 3, NULL, NULL, NULL, ?, ?)
                """,
                (gp_id, platform, now, now),
            )
            inserted += int(cur.rowcount or 0)

        log_event(
            conn,
            level="INFO",
            event_type="enqueue",
            message="Created publishing jobs for generated posts.",
            context={"inserted_jobs": inserted},
        )

    print(f"OK: Jobs created inserted={inserted}")


if __name__ == "__main__":
    main()

