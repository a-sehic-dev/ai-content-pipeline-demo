from __future__ import annotations

import os
import random
import time
from typing import Any

from db import db_conn, fetch_one, init_db, log_event
from utils import clamp, utc_now_iso


FAIL_RATE = float(os.environ.get("PIPELINE_FAIL_RATE", "0.20"))  # 20% simulated failures
RATE_DELAY_SEC = float(os.environ.get("PIPELINE_RATE_DELAY_SEC", "0.50"))
MAX_JOBS = int(os.environ.get("PIPELINE_MAX_JOBS", "0"))  # 0 means "no limit"


def _acquire_next_job(conn) -> dict[str, Any] | None:
    """
    Simple single-worker acquisition.
    If you later add multiple workers, you can switch to a 'locked_by' column and use
    UPDATE .. WHERE status='pending' AND id=? to provide a safe claim.
    """
    row = fetch_one(
        conn,
        """
        SELECT id
        FROM post_jobs
        WHERE status = 'pending'
        ORDER BY id ASC
        LIMIT 1
        """,
    )
    if not row:
        return None
    job_id = int(row["id"])

    now = utc_now_iso()
    conn.execute(
        """
        UPDATE post_jobs
        SET status = 'processing', locked_at = ?, updated_at = ?
        WHERE id = ? AND status = 'pending'
        """,
        (now, now, job_id),
    )

    job = fetch_one(
        conn,
        """
        SELECT
          pj.id AS job_id,
          pj.generated_post_id,
          pj.platform,
          pj.status,
          pj.attempts,
          pj.max_attempts,
          gp.website_id,
          gp.campaign_id,
          gp.city,
          gp.domain,
          gp.language,
          gp.service_name,
          gp.body
        FROM post_jobs pj
        JOIN generated_posts gp ON gp.id = pj.generated_post_id
        WHERE pj.id = ?
        """,
        (job_id,),
    )
    return dict(job) if job else None


def _simulate_publish(job: dict[str, Any], rng: random.Random) -> None:
    """
    Simulates platform publishing.
    In production this would call a platform API or drive Playwright/Puppeteer.
    """
    if rng.random() < FAIL_RATE:
        raise RuntimeError(f"Simulated publish failure to {job['platform']}")


def main() -> None:
    processed = 0
    rng = random.Random()

    with db_conn() as conn:
        init_db(conn)

        while True:
            if MAX_JOBS and processed >= MAX_JOBS:
                break

            job = _acquire_next_job(conn)
            if not job:
                break

            processed += 1
            job_id = int(job["job_id"])
            attempts = int(job["attempts"])
            max_attempts = int(job["max_attempts"])

            # Attempt number is 1-based for display.
            attempt_no = attempts + 1
            now = utc_now_iso()

            try:
                _simulate_publish(job, rng)
                conn.execute(
                    """
                    UPDATE post_jobs
                    SET status = 'success',
                        attempts = ?,
                        last_error = NULL,
                        completed_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (attempt_no, now, now, job_id),
                )
                log_event(
                    conn,
                    level="INFO",
                    event_type="publish",
                    message="Published post (simulated).",
                    context={
                        "job_id": job_id,
                        "attempt": attempt_no,
                        "platform": job["platform"],
                        "domain": job["domain"],
                        "city": job["city"],
                        "campaign_id": job["campaign_id"],
                        "generated_post_id": job["generated_post_id"],
                    },
                )
                print(f"SUCCESS job_id={job_id} platform={job['platform']} domain={job['domain']}")
            except Exception as e:  # noqa: BLE001 (intentional for demo worker)
                err = str(e)
                attempt_no = clamp(attempt_no, 1, 999999)
                final = attempt_no >= max_attempts

                conn.execute(
                    """
                    UPDATE post_jobs
                    SET status = ?,
                        attempts = ?,
                        last_error = ?,
                        completed_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        "failed" if final else "pending",
                        attempt_no,
                        err,
                        now if final else None,
                        now,
                        job_id,
                    ),
                )

                log_event(
                    conn,
                    level="ERROR" if final else "WARN",
                    event_type="publish",
                    message="Publish attempt failed (simulated).",
                    context={
                        "job_id": job_id,
                        "attempt": attempt_no,
                        "final": final,
                        "error": err,
                        "platform": job["platform"],
                        "domain": job["domain"],
                        "city": job["city"],
                    },
                )

                state = "FAILED" if final else "RETRY"
                print(f"{state} job_id={job_id} attempt={attempt_no}/{max_attempts} error={err}")

            # Rate limiting delay between jobs (demo).
            if RATE_DELAY_SEC > 0:
                time.sleep(RATE_DELAY_SEC)

    print(f"OK: Worker finished processed={processed}")


if __name__ == "__main__":
    main()

