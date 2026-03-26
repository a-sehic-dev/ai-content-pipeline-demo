from __future__ import annotations

import json
from pathlib import Path

from db import as_json, db_conn, init_db, log_event
from utils import normalize_platform, utc_now_iso


INPUT_PATH = Path("sample_campaign.json")


def main() -> None:
    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))

    service = str(payload["service"]).strip().lower()
    content_idea = str(payload["content_idea"]).strip()
    platforms = [normalize_platform(p) for p in payload.get("platforms", [])]
    cta = payload.get("cta")
    link = payload.get("link")

    created_at = utc_now_iso()

    with db_conn() as conn:
        init_db(conn)
        cur = conn.execute(
            """
            INSERT INTO content_campaigns
              (service_name, content_idea, cta, link, selected_platforms_json, source, created_at)
            VALUES (?, ?, ?, ?, ?, 'airtable', ?)
            """,
            (service, content_idea, cta, link, as_json(platforms), created_at),
        )
        campaign_id = int(cur.lastrowid)

        log_event(
            conn,
            level="INFO",
            event_type="sync",
            message="Synced campaign input into database (simulated Airtable -> Supabase).",
            context={"campaign_id": campaign_id, "service": service, "platforms": platforms},
        )

    print(f"OK: Inserted campaign id={campaign_id} service={service} platforms={platforms}")


if __name__ == "__main__":
    main()

