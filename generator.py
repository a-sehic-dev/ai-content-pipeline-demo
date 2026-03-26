from __future__ import annotations

import json
import random
from typing import Any

from db import Campaign, db_conn, fetch_all, get_latest_campaign, init_db, log_event
from utils import compact_whitespace, ensure_sentence_end, normalize_platform, one_of, utc_now_iso


def _lang_pack(language: str) -> dict[str, list[str]]:
    # Minimal phrase banks to keep outputs believable without calling an LLM.
    if language.lower().startswith("de"):
        return {
            "greetings": ["Hallo", "Guten Tag", "Servus", "Moin"],
            "season": ["im Frühling", "jetzt im Frühling", "zum Start in den Frühling"],
            "roof_terms": ["Dach", "Dachziegel", "Dachrinne", "First", "Abdichtung"],
            "benefits": [
                "kleine Schäden früh erkennen",
                "Folgekosten vermeiden",
                "für ein gutes Gefühl sorgen",
                "Sturmschäden rechtzeitig entdecken",
            ],
            "cta_leads": ["Kurz anfragen:", "Mehr Infos:", "Termin sichern:", "Jetzt prüfen lassen:"],
            "closing": ["Wir freuen uns auf Ihre Anfrage.", "Gerne beraten wir Sie persönlich.", "Wir sind in Ihrer Nähe."],
        }
    if language.lower().startswith("nl"):
        return {
            "greetings": ["Hoi", "Hallo", "Goedendag"],
            "season": ["in het voorjaar", "nu het voorjaar start", "dit voorjaar"],
            "roof_terms": ["dak", "dakpannen", "dakgoot", "nok", "afdichting"],
            "benefits": [
                "kleine problemen vroeg ontdekken",
                "voorkom onverwachte kosten",
                "ga met een gerust gevoel de zomer in",
                "check na wind en regen",
            ],
            "cta_leads": ["Plan je check:", "Meer info:", "Maak een afspraak:", "Bekijk details:"],
            "closing": ["We helpen je graag.", "Stuur gerust een bericht.", "Lokale service, snel geregeld."],
        }
    # fallback English
    return {
        "greetings": ["Hi", "Hello", "Hey"],
        "season": ["this spring", "as spring kicks off", "going into spring"],
        "roof_terms": ["roof", "shingles", "gutters", "flashing", "sealant"],
        "benefits": [
            "catch small issues early",
            "avoid costly surprises",
            "get peace of mind",
            "spot storm damage before it spreads",
        ],
        "cta_leads": ["Learn more:", "Book now:", "Schedule here:", "Details:"],
        "closing": ["Happy to help.", "Message us any time.", "Local team, fast response."],
    }


def _platform_style(platform: str) -> dict[str, Any]:
    p = normalize_platform(platform)
    if p == "instagram":
        return {"max_sentences": 3, "use_hashtags": True, "emoji_like": False}
    if p == "linkedin":
        return {"max_sentences": 5, "use_hashtags": False, "emoji_like": False}
    # facebook and default
    return {"max_sentences": 4, "use_hashtags": False, "emoji_like": False}


def _service_noun(service_name: str, language: str) -> str:
    s = service_name.strip().lower()
    if s == "roofing":
        return "Dach" if language.startswith("de") else ("dak" if language.startswith("nl") else "roof")
    if s == "hvac":
        return (
            "Heizung & Klima"
            if language.startswith("de")
            else ("verwarming & airco" if language.startswith("nl") else "heating & cooling")
        )
    return service_name


def _generate_post_text(
    *,
    rng: random.Random,
    campaign: Campaign,
    platform: str,
    city: str,
    language: str,
    domain: str,
    service_name: str,
    variation_index: int,
) -> tuple[str, str | None]:
    pack = _lang_pack(language)
    style = _platform_style(platform)
    service_noun = _service_noun(service_name, language.lower())

    greet = one_of(pack["greetings"], rng)
    season = one_of(pack["season"], rng)
    roof_term = one_of(pack["roof_terms"], rng)
    benefit = one_of(pack["benefits"], rng)
    closing = one_of(pack["closing"], rng)
    cta_lead = one_of(pack["cta_leads"], rng)

    # “Prompt-template” logic with controlled variation knobs.
    idea = campaign.content_idea.strip()
    cta = (campaign.cta or "").strip()
    link = (campaign.link or "").strip()

    # Make the city/service feel naturally embedded (not templated spam).
    if language.lower().startswith("de"):
        s1 = f"{greet} {city}! {season} ist ein guter Zeitpunkt für eine kurze {service_noun}-Inspektion."
        s2 = f"Wir schauen uns {roof_term} und typische Schwachstellen an – so lassen sich {benefit}."
        s3 = f"Thema: {idea} – passend für {city} und Umgebung."
        s4 = f"{cta_lead} {link}" if link else f"{ensure_sentence_end(cta) if cta else 'Melden Sie sich gerne für einen Termin.'}"
        s5 = closing
    elif language.lower().startswith("nl"):
        s1 = f"{greet} {city}! {season} is perfect voor een snelle {service_noun}-check."
        s2 = f"We kijken o.a. naar {roof_term} en bekende zwakke plekken — {benefit}."
        s3 = f"Onderwerp: {idea} (lokaal voor {city})."
        s4 = f"{cta_lead} {link}" if link else (ensure_sentence_end(cta) if cta else "Stuur ons een bericht voor een afspraak.")
        s5 = closing
    else:
        s1 = f"{greet} {city}! {season} is a great time for a quick {service_noun} check."
        s2 = f"We’ll take a look at {roof_term} and common trouble spots so you can {benefit}."
        s3 = f"Campaign focus: {idea} (tailored for {city})."
        s4 = f"{cta_lead} {link}" if link else (ensure_sentence_end(cta) if cta else "Send us a message to get on the schedule.")
        s5 = closing

    # Variation controls: reorder / drop one sentence based on variation index and platform.
    sentences = [s1, s2, s3, s4, s5]
    if variation_index == 2:
        sentences = [s1, s3, s2, s4, s5]
    elif variation_index == 3:
        sentences = [s1, s2, s4, s5]  # more direct

    max_sentences = int(style["max_sentences"])
    sentences = sentences[:max_sentences]

    body = compact_whitespace(" ".join(sentences))

    hashtags: str | None = None
    if style["use_hashtags"]:
        if language.lower().startswith("de"):
            hashtags = f"# {city} #Dachcheck #Dachinspektion #Handwerk"
        elif language.lower().startswith("nl"):
            hashtags = f"# {city} #dakcheck #dakinspectie #vakmanschap"
        else:
            hashtags = f"# {city} #roofing #inspection #local"

    return body, hashtags


def main() -> None:
    with db_conn() as conn:
        init_db(conn)

        campaign = get_latest_campaign(conn)
        if not campaign:
            raise SystemExit("No campaigns found. Run `python sync_airtable.py` first.")

        # Only generate for websites that match the campaign service.
        websites = fetch_all(
            conn,
            """
            SELECT
              w.id AS website_id,
              w.city,
              w.language,
              w.domain,
              s.name AS service_name
            FROM websites w
            JOIN services s ON s.id = w.service_id
            WHERE w.is_active = 1
              AND LOWER(s.name) = LOWER(?)
            ORDER BY w.id ASC
            """,
            (campaign.service_name,),
        )

        if not websites:
            raise SystemExit(f"No active websites found for service={campaign.service_name!r}.")

        # Optionally only generate for platforms that exist on that website.
        # (Keeps the demo realistic: you can’t publish where no account exists.)
        inserted = 0
        for w in websites:
            website_id = int(w["website_id"])
            city = str(w["city"])
            language = str(w["language"])
            domain = str(w["domain"])
            service_name = str(w["service_name"])

            active_accounts = {
                str(r["platform"])
                for r in fetch_all(
                    conn,
                    "SELECT platform FROM social_accounts WHERE website_id = ? AND is_active = 1",
                    (website_id,),
                )
            }

            for platform_raw in campaign.selected_platforms:
                platform = normalize_platform(platform_raw)
                if platform not in active_accounts:
                    continue

                for variation_index in (1, 2, 3):
                    # Stable-ish randomness so reruns are consistent for the same campaign/site/platform.
                    seed = f"{campaign.id}:{website_id}:{platform}:{variation_index}"
                    rng = random.Random(seed)

                    body, hashtags = _generate_post_text(
                        rng=rng,
                        campaign=campaign,
                        platform=platform,
                        city=city,
                        language=language,
                        domain=domain,
                        service_name=service_name,
                        variation_index=variation_index,
                    )

                    meta = {
                        "seed": seed,
                        "campaign_created_at": campaign.created_at,
                        "domain": domain,
                        "language": language,
                        "city": city,
                        "service": service_name,
                        "platform": platform,
                    }

                    cur = conn.execute(
                        """
                        INSERT OR IGNORE INTO generated_posts
                          (campaign_id, website_id, platform, variation_index,
                           language, city, domain, service_name,
                           title, body, hashtags, metadata_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            campaign.id,
                            website_id,
                            platform,
                            variation_index,
                            language,
                            city,
                            domain,
                            service_name,
                            None,
                            body,
                            hashtags,
                            json.dumps(meta, ensure_ascii=False),
                            utc_now_iso(),
                        ),
                    )
                    inserted += int(cur.rowcount or 0)

        log_event(
            conn,
            level="INFO",
            event_type="generate",
            message="Generated localized posts for latest campaign.",
            context={
                "campaign_id": campaign.id,
                "service": campaign.service_name,
                "platforms": campaign.selected_platforms,
                "inserted_posts": inserted,
            },
        )

    print(f"OK: Generated posts inserted={inserted} for campaign_id={campaign.id}")


if __name__ == "__main__":
    main()

