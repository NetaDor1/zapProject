"""
main.py
Streamlit application – ZAP GenAI Onboarding Automation
Demonstrates the full AI-powered onboarding pipeline for new business clients.
"""

import json
import os
import time
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import scraper as sc
import ai_processor as ai
import crm

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ZAP – AI Onboarding Automation",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
    /* ── Global RTL: containers only (avoid * which duplicates expander text) ── */
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"] {
        direction: rtl;
    }

    /* ── Text elements – explicit, not wildcard ── */
    h1, h2, h3, h4, h5, h6, p, li, td, th, blockquote,
    [data-testid="stMarkdownContainer"] > *,
    [data-testid="stCaptionContainer"],
    [data-testid="stAlert"] > div,
    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"],
    [data-testid="stText"],
    .stMarkdown > div {
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', 'Arial Hebrew', Arial, sans-serif;
    }

    /* ── Input fields ── */
    input, textarea, select {
        direction: rtl;
        text-align: right;
    }

    /* ── Keep code / JSON LTR ── */
    code, pre,
    [data-testid="stCode"],
    [data-testid="stJson"] {
        direction: ltr !important;
        text-align: left !important;
    }

    /* ── Fix bullet/list overflow in RTL containers ── */
    [data-testid="stMarkdownContainer"] ul,
    [data-testid="stMarkdownContainer"] ol {
        padding-right: 1.5rem;
        padding-left: 0;
        margin-right: 0;
        overflow: visible;
    }
    [data-testid="stMarkdownContainer"] li {
        list-style-position: inside;
        padding-right: 0;
    }

    /* ── Custom components ── */
    .main-title {
        font-size: 2.2rem; font-weight: 800;
        background: linear-gradient(135deg, #FF6B35, #F7C59F);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0; text-align: right;
    }
    .sub-title { color: #666; font-size: 1rem; margin-top: 4px; text-align: right; }
    .metric-pill {
        display: inline-block; background: #FF6B35; color: white;
        border-radius: 20px; padding: 3px 12px; font-size: 0.8rem;
        font-weight: 600; margin: 2px;
    }
    .crm-badge {
        background: #28a745; color: white; border-radius: 6px;
        padding: 4px 10px; font-size: 0.85rem; font-weight: 600;
    }

    /* ── Submit button – fixed color, white text, no border ── */
    [data-testid="stFormSubmitButton"] button {
        background-color: #1a2e61 !important;
        color: white !important;
        font-weight: 700 !important;
        border: none !important;
    }
    [data-testid="stFormSubmitButton"] button:hover {
        background-color: #263d7a !important;
    }
    [data-testid="stFormSubmitButton"] button p {
        color: white !important;
        font-weight: 700 !important;
    }

    /* ── Hide sidebar collapse/toggle buttons only ── */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    button[aria-label="Close sidebar"],
    button[aria-label="Open sidebar"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* ── Keep sidebar always visible and fixed width ── */
    section[data-testid="stSidebar"] {
        min-width: 22rem !important;
        max-width: 22rem !important;
        transform: translateX(0) !important;
    }

    /* ── Hide toolbar/deploy button ── */
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    #MainMenu {
        display: none !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Sidebar – configuration
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ הגדרות")

    demo_mode = st.toggle("🎭 מצב דמו (ללא API)", value=True, help="כבה כדי להשתמש ב-AI אמיתי")

    api_key_valid = False
    if not demo_mode:
        provider = "groq"
        env_var, placeholder, link = "GROQ_API_KEY", "gsk_...", "console.groq.com/keys"

        # Pre-fill from .env if available, otherwise from session
        _env_value = os.getenv(env_var, "")
        _default = _env_value if _env_value.startswith("gsk_") else st.session_state.get(f"api_key_{provider}", "")

        st.markdown(f"**🔑 {env_var}**")
        st.caption(f"קבלי מפתח חינמי: [{link}](https://{link})")
        raw_key = st.text_input(
            "API Key",
            type="password",
            value=_default,
            placeholder=placeholder,
            label_visibility="collapsed",
        )
        if raw_key:
            if raw_key.startswith("http") or " " in raw_key:
                st.error("❌ זה לא API Key – נראה שהכנסת URL או טקסט אחר.")
            elif len(raw_key) < 15:
                st.warning("⚠️ המפתח נראה קצר מדי.")
            else:
                st.session_state["api_key_groq"] = raw_key
                api_key_valid = True
                st.success("✅ מפתח תקין")
        else:
            st.warning(f"⚠️ הכניסי {env_var} כדי להמשיך")

    st.divider()
    st.markdown("### 🗂️ לקוחות ב-CRM")
    clients = crm.list_clients()
    if clients:
        for c in clients[:15]:
            if st.button(
                f"📁 {c['business_name']}",
                key=f"crm_btn_{c['crm_id']}",
                use_container_width=True,
                help=f"{c['crm_id']} | {c['created_at'][:10]}",
            ):
                rec = crm.load_client(c["crm_id"])
                if rec:
                    st.session_state["profile"] = rec["profile"]
                    st.session_state["client_card"] = rec.get("client_card", "")
                    st.session_state["onboarding_script"] = rec.get("onboarding_script", "")
                    st.session_state["crm_id"] = rec["crm_id"]
                    st.session_state["record"] = rec
                    st.rerun()
    else:
        st.caption("אין לקוחות עדיין")


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
st.markdown(
    '<p class="main-title">⚡ ZAP AI Onboarding Automation</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-title">אוטומציה מבוססת AI לסריקת נכסים דיגיטליים, '
    "יצירת כרטיס לקוח ותסריט Onboarding מותאם אישית</p>",
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------

if demo_mode:
    st.info(
        "**מצב דמו פעיל** – השדות מולאו מראש עם לקוח לדוגמה (טכנאי מזגנים, הקריות). "
        "לחץ **התחל/י את התהליך** או Enter כדי לראות את הפייפליין המלא.",
        icon="🎭",
    )

with st.form("pipeline_form"):
    st.markdown("###  הכנס את הנכסים הדיגיטליים של הלקוח")
    st.caption("הכנס לפחות כתובת אחת ולחץ Enter או על הכפתור.")

    url_col1, url_col2 = st.columns(2)
    with url_col1:
        st.markdown("##### 🏪 אתר האינטרנט של הלקוח")
        url_website = st.text_input(
            "אתר האינטרנט",
            value="https://aircon-krayot.co.il" if demo_mode else "",
            placeholder="https://www.business-name.co.il",
            help="הכתובת הראשית של אתר העסק (5 עמודים)",
            label_visibility="collapsed",
        )
    with url_col2:
        st.markdown("##### 📒 מיניסייט בדפי זהב")
        url_dapei_zahav = st.text_input(
            "מיניסייט דפי זהב",
            value="https://www.d.co.il/aircon-krayot" if demo_mode else "",
            placeholder="https://www.d.co.il/...",
            help="כתובת הפרופיל של הלקוח באתר דפי זהב",
            label_visibility="collapsed",
        )

    url_extra = st.text_input(
        "➕ URL נוסף (רשת חברתית, גוגל ביזנס וכו') – אופציונלי",
        placeholder="https://www.facebook.com/...",
    )

    st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
    _ready = demo_mode or api_key_valid
    _c1, _c2, _c3 = st.columns([2, 1, 2])
    with _c2:
        run_btn = st.form_submit_button(
            "התחל/י את התהליך",
            type="primary",
            use_container_width=True,
            disabled=not _ready,
        )
    if not _ready:
        st.error("❌ נדרש GROQ_API_KEY תקין (מתחיל ב־gsk_) כדי להמשיך")

urls_input = "\n".join(u for u in [url_website, url_dapei_zahav, url_extra] if u.strip())

if run_btn and not urls_input.strip():
    st.warning("⚠️ הכניסי לפחות כתובת URL אחת")
    run_btn = False


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------
def _friendly_error(e: Exception) -> str:
    msg = str(e).lower()
    link = "console.groq.com/keys"

    if any(x in msg for x in ["quota", "429", "rate_limit", "too many", "ratelimit"]):
        return (
            "⏳ **חרגת ממגבלת הבקשות של Groq**\n\n"
            f"המתיני כ-30 שניות ונסי שוב. בדקי ב: [{link}](https://{link})"
        )
    if any(x in msg for x in ["api_key", "invalid", "401", "unauthenticated", "api key"]):
        return (
            "❌ **מפתח Groq שגוי**\n\n"
            f"ודאי שהמפתח מתחיל ב-`gsk_` ושהעתקת אותו במלואו.\n"
            f"קבלי מפתח חדש: [{link}](https://{link})"
        )
    if "חסר" in str(e):
        return (
            "❌ **מפתח Groq לא הוזן**\n\n"
            f"הכניסי מפתח בסייד-בר. קבלי מפתח חינמי: [{link}](https://{link})"
        )
    return f"❌ **שגיאה ב-Groq:**\n\n`{str(e)}`"


if run_btn:
    urls = [u.strip() for u in urls_input.splitlines() if u.strip()]

    # Reload .env fresh every run, then override with session key if present
    if not demo_mode:
        load_dotenv(override=True)
        session_key = st.session_state.get("api_key_groq", "")
        if session_key:
            os.environ["GROQ_API_KEY"] = session_key
        ai.reset_client()

    # ── Step 1: Scraping ────────────────────────────────────────────────────
    with st.status("⏳ מריץ פייפליין...", expanded=True) as status:

        st.write("**שלב 1 – סריקת נכסים דיגיטליים** 🔍")
        scan_placeholder = st.empty()

        scraped_data = None
        if demo_mode:
            time.sleep(0.8)
            scraped_data = {
                "combined_text": (
                    "קריר-טק פתרונות מיזוג אוויר\n"
                    "שירותים: התקנת מזגנים, תיקון, תחזוקה\n"
                    "טלפון: 052-1234567\nקריית ביאליק"
                ),
                "phones": ["0521234567", "048765432"],
                "emails": ["moshe@krirtech.co.il"],
                "errors": [],
                "page_count": len(urls),
            }
            scan_placeholder.success(
                f"✅ נסרקו {len(urls)} כתובות בהצלחה (מצב דמו)"
            )
        else:
            with scan_placeholder:
                with st.spinner("סורק..."):
                    pages = sc.scan_all(urls)
                    scraped_data = sc.merge_scraped(pages)
            ok = len(urls) - len(scraped_data["errors"])
            scan_placeholder.success(f"✅ נסרקו {ok}/{len(urls)} עמודים בהצלחה")
            if scraped_data["errors"]:
                for err in scraped_data["errors"]:
                    st.warning(f"⚠️ {err}")

        # ── Step 2: AI Extraction ──────────────────────────────────────────
        st.write("**שלב 2 – חילוץ מידע באמצעות Groq AI** 🤖")
        extract_placeholder = st.empty()

        profile = None
        if demo_mode:
            time.sleep(0.6)
            profile = ai.MOCK_PROFILE.copy()
            extract_placeholder.success("✅ פרופיל עסקי חולץ בהצלחה (מצב דמו)")
        else:
            try:
                with extract_placeholder:
                    with st.spinner("מנתח..."):
                        profile = ai.extract_business_profile(scraped_data)
                extract_placeholder.success("✅ פרופיל עסקי חולץ בהצלחה")
            except Exception as e:
                status.update(label="❌ הפייפליין נעצר", state="error")
                st.error(_friendly_error(e))
                st.stop()

        # ── Step 3: Client Card ────────────────────────────────────────────
        st.write("**שלב 3 – יצירת כרטיס לקוח** 📋")
        card_placeholder = st.empty()

        client_card = None
        if demo_mode:
            time.sleep(0.6)
            client_card = ai.MOCK_CLIENT_CARD
            card_placeholder.success("✅ כרטיס לקוח נוצר (מצב דמו)")
        else:
            try:
                with card_placeholder:
                    with st.spinner("מייצר כרטיס..."):
                        client_card = ai.generate_client_card(profile)
                card_placeholder.success("✅ כרטיס לקוח נוצר")
            except Exception as e:
                status.update(label="❌ הפייפליין נעצר", state="error")
                st.error(_friendly_error(e))
                st.stop()

        # ── Step 4: Onboarding Script ──────────────────────────────────────
        st.write("**שלב 4 – בניית תסריט Onboarding** 📞")
        script_placeholder = st.empty()

        onboarding_script = None
        if demo_mode:
            time.sleep(0.6)
            onboarding_script = ai.MOCK_ONBOARDING
            script_placeholder.success("✅ תסריט Onboarding נוצר (מצב דמו)")
        else:
            try:
                with script_placeholder:
                    with st.spinner("בונה תסריט..."):
                        onboarding_script = ai.generate_onboarding_script(profile)
                script_placeholder.success("✅ תסריט Onboarding נוצר")
            except Exception as e:
                status.update(label="❌ הפייפליין נעצר", state="error")
                st.error(_friendly_error(e))
                st.stop()

        # ── Step 5: CRM + Notifications ───────────────────────────────────
        st.write("**שלב 5 – שמירה ב-CRM ושליחה אוטומטית** 💾")
        crm_placeholder = st.empty()

        time.sleep(0.4)
        record = crm.save_client(profile, client_card, onboarding_script, urls)
        crm_id = record["crm_id"]

        wa_msg = (
            f"שלום {profile.get('owner_name', '')}! "
            f"{profile.get('business_name', '')} שלך כבר פעיל בדפי זהב! 🎉 "
            "תוך 48 שעות תתחיל לקבל פניות. – צוות קבוצת זאפ"
        )
        crm.simulate_send_whatsapp(crm_id, profile.get("phone_primary", ""), wa_msg)
        crm.simulate_send_email(
            crm_id,
            profile.get("email", ""),
            "ברוך הבא לקבוצת זאפ! 🎉",
            f"שלום {profile.get('owner_name', '')},\n\nהפרופיל שלך הוקם בהצלחה.\n{client_card}",
        )
        crm.add_activity(crm_id, "onboarding_complete", "פייפליין Onboarding הושלם בהצלחה")

        crm_placeholder.success(
            f"✅ נשמר ב-CRM: **{crm_id}** | נשלחו: WhatsApp + Email"
        )

        status.update(label="✅ פייפליין הושלם בהצלחה!", state="complete")

    # ── Save to session state and rerun so the sidebar refreshes ──────────
    st.session_state["profile"] = profile
    st.session_state["client_card"] = client_card
    st.session_state["onboarding_script"] = onboarding_script
    st.session_state["crm_id"] = crm_id
    st.session_state["record"] = record
    st.rerun()


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------
if "profile" in st.session_state:
    profile = st.session_state["profile"]
    client_card = st.session_state["client_card"]
    onboarding_script = st.session_state["onboarding_script"]
    crm_id = st.session_state["crm_id"]
    record = st.session_state["record"]

    st.divider()

    # ── Profile summary card ───────────────────────────────────────────────
    da       = profile.get("digital_assets", {})
    sentiment = profile.get("customer_reviews_sentiment", "אין מידע")
    sentiment_icon = {"חיובי": "😊", "שלילי": "😟", "מעורב": "😐"}.get(sentiment, "❓")
    services = profile.get("services", [])

    with st.container(border=True):
        left_col, right_col = st.columns([3, 2])

        with left_col:
            st.markdown(
                f"### {profile.get('business_name', '—')}",
            )
            st.markdown(
                f"**{profile.get('business_type', '—')}** &nbsp;|&nbsp; "
                f"📍 {profile.get('region', '—')}",
                unsafe_allow_html=True,
            )
            if services:
                st.markdown("**שירותים:** " + " · ".join(services[:5]))

        with right_col:
            st.markdown(
                f"👤 **{profile.get('owner_name', '—')}**  \n"
                f"📱 {profile.get('phone_primary', '—')}  \n"
                f"📧 {profile.get('email') or '—'}"
            )

        st.divider()

        badge_col1, badge_col2, badge_col3, badge_col4 = st.columns(4)
        badge_col1.markdown("✅ אתר אינטרנט" if da.get("has_website") else "❌ אתר אינטרנט")
        badge_col2.markdown("✅ דפי זהב" if da.get("has_dapei_zahav") else "❌ דפי זהב")
        badge_col3.markdown("✅ רשתות חברתיות" if da.get("has_social_media") else "❌ רשתות חברתיות")
        badge_col4.markdown(f"{sentiment_icon} סנטימנט: **{sentiment}**")

    # ── Tabs ──────────────────────────────────────────────────────────────
    st.markdown(
        """
<style>
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 6px;
        background: #e8ecf5;
        padding: 8px 10px;
        border-radius: 12px;
        margin-bottom: 4px;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        background: white;
        border-radius: 8px;
        padding: 8px 18px;
        font-weight: 600;
        font-size: 0.9rem;
        border: 1.5px solid #b0bcd8;
        color: #1a2e61;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        background: #1a2e61 !important;
        color: white !important;
        border-color: #1a2e61 !important;
    }
</style>
""",
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["📋 כרטיס לקוח", "📞 תסריט Onboarding"])

    with tab1:
        with st.container(border=True):
            st.markdown(client_card)

        st.divider()

        # ── Expandable sections ────────────────────────────────────────────
        with st.expander("🔍 פרופיל גולמי"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**פרטי בסיס**")
                for key, label in [
                    ("business_name", "שם העסק"),
                    ("owner_name", "בעלים"),
                    ("business_type", "סוג עסק"),
                    ("region", "אזור"),
                    ("address", "כתובת"),
                    ("working_hours", "שעות"),
                ]:
                    st.markdown(f"**{label}:** {profile.get(key) or '—'}")

            with col_b:
                st.markdown("**קשר ושירותים**")
                st.markdown(f"**טלפון ראשי:** {profile.get('phone_primary') or '—'}")
                st.markdown(f"**טלפון נוסף:** {profile.get('phone_secondary') or '—'}")
                st.markdown(f"**אימייל:** {profile.get('email') or '—'}")
                _svc = profile.get("services", [])
                st.markdown(
                    "**שירותים:** " + " · ".join(f'<span class="metric-pill">{s}</span>' for s in _svc),
                    unsafe_allow_html=True,
                )
                _brands = profile.get("brands", [])
                st.markdown(
                    "**מותגים:** " + " · ".join(f'<span class="metric-pill">{b}</span>' for b in _brands),
                    unsafe_allow_html=True,
                )

            st.divider()
            st.markdown("**יתרונות תחרותיים:**")
            for diff in profile.get("key_differentiators", []):
                st.markdown(f"- ✅ {diff}")
            _sent = profile.get("customer_reviews_sentiment", "אין מידע")
            st.markdown(f"**סנטימנט לקוחות:** `{_sent}`")
            st.divider()
            st.markdown("**נוכחות דיגיטלית:**")
            d1, d2, d3 = st.columns(3)
            d1.metric("אתר אינטרנט", "✅" if da.get("has_website") else "❌")
            d2.metric("דפי זהב", "✅" if da.get("has_dapei_zahav") else "❌")
            d3.metric("רשתות חברתיות", "✅" if da.get("has_social_media") else "❌")

        with st.expander("💾 CRM Record"):
            st.markdown(f'<span class="crm-badge">CRM ID: {crm_id}</span>', unsafe_allow_html=True)
            st.json({
                "crm_id": record["crm_id"],
                "created_at": record["created_at"],
                "status": record["status"],
                "urls_scanned": record["urls_scanned"],
                "notifications_sent": record["notifications_sent"],
            })
            wa = next((n for n in record["notifications_sent"] if n["channel"] == "WhatsApp"), None)
            if wa:
                st.markdown("**📱 הודעת WhatsApp שנשלחה:**")
                st.info(wa["message"])

        st.divider()
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        with col_dl1:
            st.download_button(
                "⬇️ כרטיס לקוח",
                data=client_card,
                file_name=f"client_card_{crm_id}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_dl2:
            st.download_button(
                "⬇️ פרופיל JSON",
                data=json.dumps(profile, ensure_ascii=False, indent=2),
                file_name=f"profile_{crm_id}.json",
                mime="application/json",
                use_container_width=True,
            )
        with col_dl3:
            st.download_button(
                "⬇️ רשומת CRM",
                data=json.dumps(record, ensure_ascii=False, indent=2),
                file_name=f"crm_{crm_id}.json",
                mime="application/json",
                use_container_width=True,
            )

    with tab2:
        with st.container(border=True):
            st.markdown(onboarding_script)
        st.divider()
        st.download_button(
            "⬇️ הורד תסריט (Markdown)",
            data=onboarding_script,
            file_name=f"onboarding_{crm_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )


