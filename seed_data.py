from __future__ import annotations

from db import db_conn, init_db, log_event
from utils import normalize_platform, utc_now_iso


def main() -> None:
    created_at = utc_now_iso()

    with db_conn() as conn:
        init_db(conn)

        services = ["roofing", "hvac"]
        for name in services:
            conn.execute(
                "INSERT OR IGNORE INTO services (name, created_at) VALUES (?, ?)",
                (name, created_at),
            )

        service_id = {
            r["name"]: int(r["id"])
            for r in conn.execute("SELECT id, name FROM services").fetchall()
        }

        # At least 6 websites across multiple cities, multiple services.
        websites = [
            # roofing (DE/AT/CH/NL)
            ("roofing", "Berlin", "DE", "de", "berlin-roofing.example", "Berlin Roofing Co."),
            ("roofing", "Munich", "DE", "de", "munich-roofing.example", "Munich Roofing Co."),
            ("roofing", "Hamburg", "DE", "de", "hamburg-roofing.example", "Hamburg Roofing Co."),
            ("roofing", "Vienna", "AT", "de", "vienna-roofing.example", "Vienna Roofing Co."),
            ("roofing", "Zurich", "CH", "de", "zurich-roofing.example", "Zurich Roofing Co."),
            ("roofing", "Amsterdam", "NL", "nl", "amsterdam-roofing.example", "Amsterdam Roofing Co."),
            # hvac (add a couple so the service filter matters)
            ("hvac", "Berlin", "DE", "de", "berlin-hvac.example", "Berlin HVAC Service"),
            ("hvac", "Vienna", "AT", "de", "vienna-hvac.example", "Vienna HVAC Service"),
        ]

        for svc, city, country, language, domain, brand in websites:
            conn.execute(
                """
                INSERT OR IGNORE INTO websites
                  (service_id, city, country, language, domain, brand_name, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (service_id[svc], city, country, language, domain, brand, created_at),
            )

        website_rows = conn.execute(
            "SELECT id, domain FROM websites WHERE is_active = 1"
        ).fetchall()
        website_id_by_domain = {str(r["domain"]): int(r["id"]) for r in website_rows}

        # Multiple platforms per website.
        platforms = ["facebook", "instagram", "linkedin"]
        for domain, wid in website_id_by_domain.items():
            base_handle = domain.replace(".example", "").replace("-", "")
            for p in platforms:
                platform = normalize_platform(p)
                handle = f"@{base_handle}_{platform}"
                conn.execute(
                    """
                    INSERT OR IGNORE INTO social_accounts
                      (website_id, platform, handle, external_account_id, is_active, created_at)
                    VALUES (?, ?, ?, ?, 1, ?)
                    """,
                    (wid, platform, handle, f"{platform}:{base_handle}", created_at),
                )

        log_event(
            conn,
            level="INFO",
            event_type="seed",
            message="Seeded services, websites, and social accounts.",
            context={
                "services": services,
                "website_count": len(website_id_by_domain),
                "platforms_per_website": platforms,
            },
        )

    print("OK: Seed data inserted into SQLite.")


if __name__ == "__main__":
    main()

