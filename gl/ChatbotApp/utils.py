# ============================================================
# 🤖 A2A INTELLIGENT STARTUP & INVESTMENT AGENT
# ============================================================

import google.generativeai as genai
import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils.timezone import now

from Startup.models import Startup
from Investissement.models import Investissement
from StartupMembers.models import StartupMember


# ============================================================
# 🔑 GEMINI CONFIGURATION
# ============================================================

genai.configure(
    api_key="AIzaSyCWOKzlgCG8_hRg6obVSyG7N1tP4A3vsgs"   # NEVER hardcode keys
)
# ============================================================
# 🌍 DOMAIN CONSTANTS (AGENT KNOWLEDGE)
# ============================================================

DEFAULT_CURRENCY = "TND"  # Tunisian Dinar


# ============================================================
# 🔐 PERMISSION CORE (SINGLE SOURCE OF TRUTH)
# ============================================================

def can_manage_startup(user, startup: Startup) -> bool:
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser or user.is_staff:
        return True

    if startup.founder_id == user.id:
        return True

    return StartupMember.objects.filter(
        user=user,
        startup=startup,
        is_lead=True
    ).exists()

# ============================================================
# 🧠 CATEGORY PARSING UTIL
# ============================================================

def parse_categories(category_str: str) -> list[str]:
    if not category_str:
        return []
    return [
        c.strip().lower()
        for c in category_str.split("/")
        if c.strip()
    ]


def parse_query_categories(query: str) -> list[str]:
    if not query:
        return []
    return [
        c.strip().lower()
        for c in query.split("/")
        if c.strip()
    ]


# ============================================================
# 📌 BASIC STARTUP TOOLS
# ============================================================

def list_startups():
    return [
        {
            "name": s.nom_startup,
            "status": s.statut,
            "categories": parse_categories(s.category),
            "funds": f"{s.fond_actuel} {DEFAULT_CURRENCY}",
            "goal": f"{s.fond_desire} {DEFAULT_CURRENCY}",
        }
        for s in Startup.objects.all()
    ]


def get_startup_details(name: str):
    try:
        s = Startup.objects.get(nom_startup__iexact=name)
        return {
            "name": s.nom_startup,
            "description": s.description,
            "categories": parse_categories(s.category),
            "status": s.statut,
            "funds": s.fond_actuel,
            "goal": s.fond_desire,
            "progress_pct": round((s.fond_actuel / s.fond_desire) * 100, 2)
            if s.fond_desire else 0,
            "founder": s.founder.username
        }
    except Startup.DoesNotExist:
        return {"error": "Startup not found"}


# ============================================================
# 🏆 FUNDING ANALYTICS
# ============================================================

def get_most_funded_startup():
    s = Startup.objects.order_by('-fond_actuel').first()
    if not s:
        return {"error": "No startups found"}

    return {
        "name": s.nom_startup,
        "funds": f"{s.fond_actuel} {DEFAULT_CURRENCY}",
        "goal": f"{s.fond_desire} {DEFAULT_CURRENCY}",
        "categories": parse_categories(s.category),
        "status": s.statut
    }


def list_top_startups(limit: int = 5, category: str | None = None):
    query_categories = parse_query_categories(category)

    startups = Startup.objects.all()
    matched = []

    for s in startups:
        startup_categories = parse_categories(s.category)

        # DEBUG SAFETY (you can remove later)
        # print("STARTUP:", s.nom_startup, startup_categories)

        if query_categories:
            if not any(q in startup_categories for q in query_categories):
                continue

        matched.append(s)

    matched = sorted(
        matched,
        key=lambda s: s.fond_actuel,
        reverse=True
    )[:limit]

    return [
        {
            "name": s.nom_startup,
            "categories": parse_categories(s.category),
            "funds": f"{s.fond_actuel} TND",
            "goal": f"{s.fond_desire} TND",
            "progress_pct": round(
                (s.fond_actuel / s.fond_desire) * 100, 2
            ) if s.fond_desire else 0
        }
        for s in matched
    ]

# ============================================================
# 📉 NATURAL-LANGUAGE STYLE QUERIES
# ============================================================

def find_underfunded_startups(
    category: str | None = None,
    created_year: int | None = None,
    max_progress_pct: float = 50
):
    results = []
    target_category = category.lower() if category else None

    for s in Startup.objects.all():
        categories = parse_categories(s.category)

        if target_category and target_category not in categories:
            continue

        if created_year and s.date_creation.year != created_year:
            continue

        if not s.fond_desire:
            continue

        progress = (s.fond_actuel / s.fond_desire) * 100

        if progress <= max_progress_pct:
            results.append({
                "name": s.nom_startup,
                "categories": categories,
                "created": s.date_creation.isoformat(),
                "funds": f"{s.fond_actuel} TND",
                "goal": f"{s.fond_desire} TND",
                "progress_pct": round(progress, 2)
            })

    return results

def search_startups(
    category: str | None = None,
    status: str | None = None,
    min_funding: float | None = None,
    max_funding: float | None = None
):
    target_category = category.lower() if category else None
    results = []

    for s in Startup.objects.all():
        categories = parse_categories(s.category)

        if target_category and target_category not in categories:
            continue
        if status and s.statut != status:
            continue
        if min_funding is not None and s.fond_actuel < min_funding:
            continue
        if max_funding is not None and s.fond_actuel > max_funding:
            continue

        results.append({
            "name": s.nom_startup,
            "categories": categories,
            "funds": f"{s.fond_actuel} TND",
            "goal": f"{s.fond_desire} TND",
            "status": s.statut
        })

    return results


# ============================================================
# 💰 INVESTMENT ANALYTICS (ROI & TIMELINES)
# ============================================================

def investment_summary_for_startup(startup_name: str):
    try:
        startup = Startup.objects.get(nom_startup__iexact=startup_name)
    except Startup.DoesNotExist:
        return {"error": "Startup not found"}

    investments = Investissement.objects.filter(
        startup=startup,
        statut="accepted"
    )

    total_invested = investments.aggregate(
        total=Sum("montant")
    )["total"] or 0

    timeline = list(
        investments.order_by("date")
        .values("date", "montant")
    )

    return {
        "startup": startup.nom_startup,
        "total_invested": total_invested,
        "funding_goal": startup.fond_desire,
        "progress_pct": round((total_invested / startup.fond_desire) * 100, 2)
        if startup.fond_desire else 0,
        "investment_timeline": timeline
    }


def estimate_roi_proxy(startup_name: str):
    try:
        startup = Startup.objects.get(nom_startup__iexact=startup_name)
    except Startup.DoesNotExist:
        return {"error": "Startup not found"}

    invested = Investissement.objects.filter(
        startup=startup,
        statut="accepted"
    ).aggregate(total=Sum("montant"))["total"] or 0

    if invested == 0:
        return {
            "startup": startup.nom_startup,
            "roi_proxy": None,
            "note": "No accepted investments yet"
        }

    roi = (startup.fond_actuel - invested) / invested

    return {
        "startup": startup.nom_startup,
        "roi_proxy": round(roi, 3),
        "invested": invested,
        "current_funds": startup.fond_actuel
    }


# ============================================================
# 👥 MEMBERSHIP MANAGEMENT
# ============================================================

def add_startup_member(
    startup_name: str,
    username: str,
    role: str,
    requesting_user_id: int
):
    try:
        user = get_user_model().objects.get(id=requesting_user_id)
        startup = Startup.objects.get(nom_startup__iexact=startup_name)

        if not can_manage_startup(user, startup):
            return {"error": "Permission denied"}

        member_user = get_user_model().objects.get(username=username)

        StartupMember.objects.create(
            user=member_user,
            startup=startup,
            role=role
        )

        return {"success": f"{username} added to {startup_name}"}

    except Exception as e:
        return {"error": str(e)}


def promote_member_to_lead(
    startup_name: str,
    username: str,
    requesting_user_id: int
):
    try:
        user = get_user_model().objects.get(id=requesting_user_id)
        startup = Startup.objects.get(nom_startup__iexact=startup_name)

        if not can_manage_startup(user, startup):
            return {"error": "Permission denied"}

        member = StartupMember.objects.get(
            user__username=username,
            startup=startup
        )
        member.is_lead = True
        member.save()

        return {"success": f"{username} promoted to lead"}

    except StartupMember.DoesNotExist:
        return {"error": "Member not found"}


# ============================================================
# 🗑️ SAFE UPDATE & DELETE
# ============================================================

def update_startup(
    startup_name: str,
    updates: dict,
    requesting_user_id: int
):
    try:
        user = get_user_model().objects.get(id=requesting_user_id)
        startup = Startup.objects.get(nom_startup__iexact=startup_name)

        if not can_manage_startup(user, startup):
            return {"error": "Permission denied"}

        allowed = {"description", "fond_desire", "statut", "category"}

        for field, value in updates.items():
            if field in allowed:
                setattr(startup, field, value)

        startup.save()
        return {"success": "Startup updated"}

    except Startup.DoesNotExist:
        return {"error": "Startup not found"}


def delete_startup_secure(startup_name: str, requesting_user_id: int):
    try:
        user = get_user_model().objects.get(id=requesting_user_id)
        startup = Startup.objects.get(nom_startup__iexact=startup_name)

        if not can_manage_startup(user, startup):
            return {"error": "Permission denied"}

        startup.delete()
        return {"success": "Startup deleted"}

    except Startup.DoesNotExist:
        return {"error": "Startup not found"}

from datetime import datetime
from django.utils import timezone
from django.db import IntegrityError

REQUIRED_STARTUP_FIELDS = ["nom_startup", "date_creation", "description", "fond_desire"]

def _parse_date_flexible(value):
    """
    Accepts:
      - 'YYYY-MM-DD'
      - 'DD/MM/YYYY'
      - 'DD-MM-YYYY'
    Returns a python date.
    """
    if value is None:
        return None
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        # already a date/datetime
        return value.date() if hasattr(value, "date") else value

    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def create_startup_via_chat(
    requesting_user_id: int,
    nom_startup: str | None = None,
    date_creation: str | None = None,
    description: str | None = None,
    fond_desire: float | None = None,
    category: str | None = None,
    statut: str | None = "pending",
):
    """
    Create a Startup through the chatbot.
    If required fields are missing/invalid, returns a structured response so the bot can ask follow-ups.
    """
    # --- Auth / user ---
    try:
        user = get_user_model().objects.get(id=requesting_user_id)
    except get_user_model().DoesNotExist:
        return {"error": "User not found"}

    # --- Clean inputs ---
    data = {
        "nom_startup": (nom_startup or "").strip() or None,
        "date_creation": date_creation,
        "description": (description or "").strip() or None,
        "fond_desire": fond_desire,
        "category": (category or "").strip() or None,
        "statut": (statut or "pending").strip(),
    }

    # --- Validate required fields ---
    missing = []
    if not data["nom_startup"]:
        missing.append("nom_startup")
    if not data["description"]:
        missing.append("description")
    if data["fond_desire"] is None:
        missing.append("fond_desire")

    parsed_date = _parse_date_flexible(data["date_creation"])
    if not parsed_date:
        missing.append("date_creation")

    # If anything missing/invalid → ask user for those only
    if missing:
        # Helpful per-field prompts
        hints = {
            "nom_startup": "Nom de la startup (ex: 'EduLife')",
            "date_creation": "Date de création (YYYY-MM-DD ou DD/MM/YYYY)",
            "description": "Description courte (1–5 phrases)",
            "fond_desire": "Fonds désirés (nombre en TND, ex: 50000)",
        }
        return {
            "status": "missing_fields",
            "missing_fields": missing,
            "message": "J’ai besoin de quelques infos avant de créer la startup.",
            "field_hints": {k: hints[k] for k in missing},
            "received": {k: data[k] for k in data if data[k] is not None and k != "date_creation"},
        }

    # --- Extra validation ---
    try:
        fond = float(data["fond_desire"])
        if fond <= 0:
            return {
                "status": "invalid_value",
                "field": "fond_desire",
                "message": "fond_desire doit être > 0 (ex: 50000).",
            }
    except Exception:
        return {
            "status": "invalid_value",
            "field": "fond_desire",
            "message": "fond_desire doit être un nombre (ex: 50000).",
        }

    # Optional: avoid duplicates by name (case-insensitive)
    exists = Startup.objects.filter(nom_startup__iexact=data["nom_startup"]).exists()
    if exists:
        return {
            "status": "already_exists",
            "message": f"Une startup nommée '{data['nom_startup']}' existe déjà. Donne un autre nom.",
        }

    # --- Create ---
    try:
        s = Startup.objects.create(
            nom_startup=data["nom_startup"],
            date_creation=parsed_date,
            description=data["description"],
            fond_desire=fond,
            fond_actuel=0,
            statut=data["statut"],
            category=data["category"],
            founder=user,
        )
        return {
            "status": "success",
            "message": "Startup créée avec succès ✅",
            "startup": {
                "id_startup": s.id_startup,
                "nom_startup": s.nom_startup,
                "date_creation": s.date_creation.isoformat(),
                "fond_desire": s.fond_desire,
                "fond_actuel": s.fond_actuel,
                "statut": s.statut,
                "category": parse_categories(s.category),
                "founder": user.username,
            }
        }
    except IntegrityError as e:
        return {"error": f"DB integrity error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# 🤖 AGENT CHAT ENTRY POINT (A2A)
# ============================================================

TOOLS = [
    list_startups,
    get_startup_details,
    get_most_funded_startup,
    list_top_startups,
    find_underfunded_startups,
    search_startups,
    investment_summary_for_startup,
    estimate_roi_proxy,
    add_startup_member,
    promote_member_to_lead,
    update_startup,
    delete_startup_secure,
    create_startup_via_chat
]


def get_chat_response(history, user_message):
    system_context = (
    "You are an intelligent startup and investment assistant.\n"
    "The default currency is Tunisian Dinar (TND).\n"
    "A startup may belong to multiple categories.\n"
    "Categories are separated by '/'.\n"
    "Treat each category as independent (e.g. 'Health / Lifestyle' = Health AND Lifestyle).\n"
    "When filtering by category, include startups that contain the category among their list."
)


    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        tools=TOOLS
    )

    chat = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [system_context]
            }
        ] + history
    )
    response = chat.send_message(user_message)

    while response.parts and response.parts[0].function_call:
        fc = response.parts[0].function_call
        fn = next((f for f in TOOLS if f.__name__ == fc.name), None)

        if not fn:
            break

        result = fn(**fc.args)

        response = chat.send_message(
            genai.protos.Content(
                parts=[genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=fc.name,
                        response={"result": result}
                    )
                )]
            )
        )

    return response.text
