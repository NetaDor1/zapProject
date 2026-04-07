"""
ai_processor.py
All AI interactions – extraction, client card generation, onboarding script.
Uses Groq (llama-3.1-8b-instant) exclusively.
"""
from __future__ import annotations

import json
import os
import re
from groq import Groq

# ── Client ────────────────────────────────────────────────────────────────────
_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    return _client


def reset_client() -> None:
    """Force re-creation of the Groq client (call after updating the API key)."""
    global _client
    _client = None


def _chat(system: str, user: str, temperature: float = 0.4, json_mode: bool = False) -> str:
    """Send a chat request to Groq and return the text response."""
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    resp = _get_client().chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=temperature,
        **kwargs,
    )
    return resp.choices[0].message.content


# ── Prompts ───────────────────────────────────────────────────────────────────
EXTRACTION_SYSTEM = """אתה מנתח נתונים עסקיים.
חוק מוחלט: חלץ רק מידע שמופיע במפורש בטקסט. אל תמציא, אל תשלים, אל תנחש.
אם מידע לא מופיע – השתמש ב-null. עדיף null על פני המצאה.
הגבל: services ו-brands ו-key_differentiators – לכל היותר 5 פריטים כל אחד.
החזר JSON תקין בלבד – מתחיל ב-{ ומסתיים ב-} – ללא טקסט לפני או אחרי, ללא ```."""

EXTRACTION_PROMPT = """מהטקסט הבא חלץ מידע עסקי והחזר JSON עם המבנה הבא:
{{
  "business_name": "שם העסק",
  "owner_name": "שם הבעלים",
  "business_type": "סוג העסק",
  "region": "אזור פעילות",
  "address": "כתובת מלאה",
  "working_hours": "שעות פעילות",
  "phone_primary": "טלפון ראשי (ספרות בלבד)",
  "phone_secondary": "טלפון נוסף אם קיים",
  "email": "אימייל",
  "services": ["שירות 1", "שירות 2"],
  "brands": ["מותג 1", "מותג 2"],
  "key_differentiators": ["יתרון 1", "יתרון 2"],
  "customer_reviews_sentiment": "חיובי/שלילי/מעורב/אין מידע",
  "digital_assets": {{
    "has_website": true,
    "has_dapei_zahav": true,
    "has_social_media": false
  }}
}}

אם מידע חסר – השתמש ב-null או ב-[].

טלפונות שנמצאו: {phones}
אימיילים שנמצאו: {emails}
כתובות שנמצאו: {addresses}
שעות שנמצאו: {hours}

טקסט גולמי:
{text}"""

CLIENT_CARD_SYSTEM = """אתה מומחה לכתיבה עסקית בעברית.
כתוב כרטיס לקוח מקצועי לפי התבנית המדויקת שסופקה. החזר Markdown בלבד.
חוק מוחלט: השתמש אך ורק במידע שמופיע בפרופיל. אל תמציא שירותים, מחירים, או פרטים שלא נמצאים בפרופיל.
אם שדה הוא null או ריק – השמט אותו לחלוטין."""

CLIENT_CARD_PROMPT = """צור כרטיס לקוח לפי התבנית הבאה בדיוק. אל תוסיף סעיפים שאינם בתבנית.

## 📋 כרטיס לקוח – {business_name}

### 1. סיכום עסקי
[2-3 משפטים על העסק: מה הוא עושה, באיזה אזור, כמה ותק/ייחוד אם קיים בפרופיל]

### 2. פרטי קשר
{contact_lines}

### 3. שירותים ומוצרים
{services_line}
{brands_line}

### 4. נוכחות דיגיטלית
{digital_lines}

### 5. יתרונות תחרותיים
{differentiators_lines}

### 6. המלצות ראשוניות למפיק
{recommendations}

---
פרופיל:
{profile_json}"""

ONBOARDING_SYSTEM = """אתה מומחה CX וקליטת עסקים לפלטפורמה דיגיטלית כמו קבוצת זאפ.
החזר Markdown בלבד – ללא טקסט לפני או אחרי, ללא סוגריים מרובעים בפלט.
כתוב בעברית, ממוקד, מעשי ורלוונטי לסוג העסק הספציפי.

כללים לכל סעיף:
• שאלות קליטה: שאל רק שאלות הנחוצות להשלמת מידע חסר או לא ברור. תעדף שאלות המשפיעות על רכישת לקוחות והמרה. שמור עליהן קצרות, טבעיות ורלוונטיות לשיחת טלפון.
• שלבי קליטה: תאר פעולות ספציפיות שZap מבצעת לסוג עסק זה – לא גנריות. שמור על פרקטי ותפעולי.
• KPIs: 4-6 מדדים מדידים (שיחות, לידים, המרות, נראות) – פשוטים וניתנים לפעולה.
• תובנות AI: ציין רק שדות שערכם null בפועל בפרופיל ומה לשפר. אם הכל קיים – כתוב ✅ בלבד."""

ONBOARDING_PROMPT = """בהתבסס על הפרופיל שלמטה, צור מסמך קליטה לפי התבנית הבאה בדיוק.
חוק מוחלט: אל תכתוב סוגריים מרובעים [] בפלט – כתוב תוכן אמיתי בלבד.

---

## 📞 תסריט קליטה – {business_name}

### 🎙️ פתיחה (20 שניות)
שלום [שם בעלים], מדבר ___ מקבוצת זאפ. [משפט אחד על מטרת השיחה המותאם לסוג העסק]

---

### 🔹 הצעת ערך (30 שניות)
[1-2 משפטים על הערך שקבוצת זאפ מביאה לסוג עסק זה ספציפית]

---

### ❓ שאלות קליטה חכמות

- ✦ [שאלה 1]
- ✦ [שאלה 2]
- ✦ [שאלה 3]
- ✦ [שאלה 4]
- ✦ [שאלה 5]

---

### 🏗️ שלבי הגדרת הקליטה

1. **[שם שלב]** – [פעולה]
2. **[שם שלב]** – [פעולה]
3. **[שם שלב]** – [פעולה]
4. **[שם שלב]** – [פעולה]

---

### 📊 KPIs למעקב (30 יום ראשונים)

- 📈 **[מדד]:** [יעד]
- 📩 **[מדד]:** [יעד]
- 💰 **[מדד]:** [יעד]
- ⭐ **[מדד]:** [יעד]
- 🔄 **[מדד]:** [יעד]

---

### 🤖 תובנות AI

- ⚠ **חסר:** [שדה] — [המלצה]

---

### 💬 הודעת WhatsApp אוטומטית
[הודעה קצרה ואישית – עד 3 שורות, מסתיימת ב-😊]

---

פרופיל:
{profile_json}"""


# ── Public functions ───────────────────────────────────────────────────────────
def _repair_truncated_json(text: str) -> str:
    """Close any unclosed brackets/braces in a truncated JSON string."""
    stack = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]":
                if stack and stack[-1] == ch:
                    stack.pop()
    # Close open structures in reverse order
    closing = "".join(reversed(stack))
    return text.rstrip().rstrip(",") + closing


def _parse_json_safe(raw: str) -> dict:
    """Parse JSON from AI response, handling common formatting issues."""
    text = raw.strip()

    # 1. Strip markdown code fences  ``` or ```json
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()

    # 2. Try as-is first (the happy path)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Extract the substring between first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    # 4. Response starts with a key (e.g. `"business_name": ...`) – wrap with {}
    if text.startswith('"'):
        try:
            candidate = "{" + text + "}"
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 5. Try repairing truncated JSON
    try:
        repaired = _repair_truncated_json(text)
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # 6. Nothing worked – raise with the raw content for easier debugging
    raise ValueError(f"לא ניתן לפרסר את תשובת ה-AI כ-JSON.\nתשובה גולמית:\n{raw[:500]}")


def extract_business_profile(scraped_data: dict) -> dict:
    """Extract structured business profile from scraped text using Groq."""
    prompt = EXTRACTION_PROMPT.format(
        phones=", ".join(scraped_data.get("phones", [])) or "לא נמצא",
        emails=", ".join(scraped_data.get("emails", [])) or "לא נמצא",
        addresses=", ".join(scraped_data.get("addresses", [])) or "לא נמצא",
        hours=", ".join(scraped_data.get("hours", [])) or "לא נמצא",
        text=scraped_data.get("combined_text", "")[:3000],
    )
    raw = _chat(EXTRACTION_SYSTEM, prompt, temperature=0.1, json_mode=True)
    return _parse_json_safe(raw)


def generate_client_card(profile: dict) -> str:
    """Generate a formatted Hebrew client card for the Zap producer."""
    da = profile.get("digital_assets", {})

    # Build contact lines – skip nulls
    contact_parts = []
    if profile.get("owner_name"):
        contact_parts.append(f"- 👤 **בעלים:** {profile['owner_name']}")
    if profile.get("phone_primary"):
        contact_parts.append(f"- 📱 **נייד:** {profile['phone_primary']}")
    if profile.get("phone_secondary"):
        contact_parts.append(f"- ☎️ **נייח:** {profile['phone_secondary']}")
    if profile.get("email"):
        contact_parts.append(f"- 📧 **אימייל:** {profile['email']}")
    if profile.get("address"):
        contact_parts.append(f"- 📍 **כתובת:** {profile['address']}")
    if profile.get("working_hours"):
        contact_parts.append(f"- 🕐 **שעות:** {profile['working_hours']}")
    contact_lines = "\n".join(contact_parts) if contact_parts else "— לא סופק —"

    # Services / brands
    services = profile.get("services", [])
    services_line = ("**שירותים:** " + " | ".join(services)) if services else ""
    brands = profile.get("brands", [])
    brands_line = ("**מותגים:** " + " · ".join(brands)) if brands else ""

    # Digital presence
    digital_parts = []
    digital_parts.append("- ✅ אתר אינטרנט פעיל" if da.get("has_website") else "- ❌ אתר אינטרנט — **הזדמנות**")
    digital_parts.append("- ✅ מיניסייט בדפי זהב" if da.get("has_dapei_zahav") else "- ❌ מיניסייט בדפי זהב — **הזדמנות**")
    digital_parts.append("- ✅ רשתות חברתיות" if da.get("has_social_media") else "- ❌ רשתות חברתיות — **הזדמנות לשיפור**")
    digital_lines = "\n".join(digital_parts)

    # Differentiators
    diffs = profile.get("key_differentiators", [])
    differentiators_lines = "\n".join(f"- ⭐ {d}" for d in diffs) if diffs else "— לא סופק —"

    prompt = CLIENT_CARD_PROMPT.format(
        business_name=profile.get("business_name", "הלקוח"),
        contact_lines=contact_lines,
        services_line=services_line,
        brands_line=brands_line,
        digital_lines=digital_lines,
        differentiators_lines=differentiators_lines,
        recommendations="[כתוב 3-4 המלצות ספציפיות למפיק בהתבסס על מה שחסר בפרופיל]",
        profile_json=json.dumps(profile, ensure_ascii=False, indent=2),
    )
    return _chat(CLIENT_CARD_SYSTEM, prompt)


def generate_onboarding_script(profile: dict) -> str:
    """Generate a structured onboarding call script."""
    prompt = ONBOARDING_PROMPT.format(
        business_name=profile.get("business_name", "הלקוח"),
        profile_json=json.dumps(profile, ensure_ascii=False, indent=2),
    )
    return _chat(ONBOARDING_SYSTEM, prompt)


# ── Mock data (demo mode) ─────────────────────────────────────────────────────
MOCK_PROFILE: dict = {
    "business_name": "קריר-טק פתרונות מיזוג אוויר",
    "owner_name": "אבי כהן",
    "business_type": "טכנאי מזגנים",
    "region": "קריית ביאליק, הקריות",
    "address": "רחוב הרצל 12, קריית ביאליק",
    "working_hours": "ראשון–חמישי 08:00–18:00, שישי 08:00–13:00",
    "phone_primary": "0521234567",
    "phone_secondary": "048765432",
    "email": "moshe@krirtech.co.il",
    "services": ["התקנת מזגנים", "תיקון", "תחזוקה שנתית", "ניקוי", "מיזוג מרכזי"],
    "brands": ["LG", "מידיאה", "Gree", "פנסוניק", "מיצובישי"],
    "key_differentiators": [
        "שירות חירום 24/7",
        "ניסיון של 15 שנה",
        "אחריות על כל עבודה",
        "מחירים תחרותיים",
    ],
    "customer_reviews_sentiment": "חיובי",
    "digital_assets": {
        "has_website": True,
        "has_dapei_zahav": True,
        "has_social_media": False,
    },
}

MOCK_CLIENT_CARD: str = """## 📋 כרטיס לקוח – קריר-טק פתרונות מיזוג אוויר

### 1. סיכום עסקי
קריר-טק היא חברת שירותי מיזוג אוויר מקצועית הפועלת באזור הקריות מזה 15 שנה.
העסק מתמחה בהתקנה, תיקון ותחזוקה של מזגנים לבתים ולעסקים, עם דגש על שירות חירום ואיכות גבוהה.

### 2. פרטי קשר
- 👤 **בעלים:** אבי כהן
- 📱 **נייד:** 052-1234567
- ☎️ **נייח:** 04-8765432
- 📧 **אימייל:** moshe@krirtech.co.il
- 📍 **כתובת:** רחוב הרצל 12, קריית ביאליק

### 3. שירותים ומוצרים
**שירותים:** התקנת מזגנים | תיקון | תחזוקה שנתית | ניקוי | מיזוג מרכזי

**מותגים:** LG · מידיאה · Gree · פנסוניק · מיצובישי

### 4. נוכחות דיגיטלית
- ✅ אתר אינטרנט פעיל
- ✅ מיניסייט בדפי זהב
- ❌ רשתות חברתיות – **הזדמנות לשיפור**

### 5. יתרונות תחרותיים
- ⭐ שירות חירום 24/7
- ⭐ ניסיון של 15 שנה באזור הקריות
- ⭐ אחריות מלאה על כל עבודה
- ⭐ מחירים תחרותיים

### 6. המלצות ראשוניות למפיק
1. להציע חבילת **רשתות חברתיות** – העסק לא נוכח ב-Facebook/Instagram
2. לעדכן **שעות פעילות** בדפי זהב ובאתר
3. לצרף **גלריית תמונות** של עבודות
4. להוסיף **ביקורות לקוחות** למיניסייט"""

MOCK_ONBOARDING: str = """## 📞 תסריט קליטה – קריר-טק פתרונות מיזוג אוויר

### 🎙️ פתיחה (20 שניות)
שלום אבי, מדבר ___ מקבוצת זאפ. רצינו לעזור לך להגדיל את כמות הלקוחות שמוצאים אותך באינטרנט באזור הקריות.

---

### 🔹 הצעת ערך (30 שניות)
אנחנו מביאים לך לקוחות שמחפשים טכנאי מזגנים בדיוק באזור שלך – דרך דפי זהב ואתר האינטרנט שלך, עם מדידה ברורה של תוצאות.

---

### ❓ שאלות קליטה חכמות

- ✦ איך מגיעים אליך לקוחות כיום — המלצות, גוגל, או דרך מודעות?
- ✦ האם אתה מוכן לקבל פניות דרך WhatsApp, או שאתה מעדיף טלפון בלבד?
- ✦ כמה זמן בממוצע לוקח לך לחזור ללקוח שפנה אליך?
- ✦ האם יש לך תמונות עבודה שנוכל להעלות לגלריה בדפי זהב?
- ✦ כמה לקוחות חדשים בחודש תחשיב כהצלחה עבורך?

---

### 🏗️ שלבי הגדרת הקליטה

1. **הגדרת אזור שירות** – סימון מדויק של הקריות + ערי הסביבה במפה בדפי זהב
2. **העלאת גלריה** – 5 תמונות התקנה/תיקון עם כיתוב מותג וסוג מזגן
3. **הפעלת WhatsApp לידים** – חיבור מספר עסקי וכפתור CTA בפרופיל
4. **הגדרת התראות** – ווידוא שהלקוח מקבל SMS/WhatsApp על כל פנייה חדשה

---

### 📊 KPIs למעקב (30 יום ראשונים)

- 📈 **חשיפות בדפי זהב:** יעד 500+ בחודש
- 📩 **לידים נכנסים:** יעד 10+ פניות
- 💰 **המרה לעסקה:** יעד 30% מהפניות
- ⭐ **דירוג ממוצע:** שמירה על 4.5+ כוכבים
- 🔄 **זמן תגובה ללקוח:** עד 2 שעות

---

### 🤖 תובנות AI

- ⚠ **חסר:** רשתות חברתיות — לשאול אם קיים פייסבוק/אינסטגרם
- ⚠ **חסר:** גלריית תמונות — לבקש 3–5 תמונות עבודות לדוגמה

---

### 💬 הודעת WhatsApp אוטומטית
שלום אבי! קריר-טק שלך כבר פעיל בדפי זהב! 🎉
תוך 48 שעות תתחיל לקבל פניות מלקוחות באזור הקריות.
לכל שאלה – צוות קבוצת זאפ זמין עבורך 😊"""
