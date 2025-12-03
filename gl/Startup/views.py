from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db import models
from django.db.models import Sum
from django.db import models

import json
import re
import requests
from urllib.parse import urlparse
import os

from .models import Startup
import Startup.templatetags.startup_extras as startup_tags


def _validate_startup_payload(nom, desc, cat, fond_desire):
    """
    Shared validation logic for creating startups (form + chatbot).
    Returns (errors_dict, cleaned_fond_val_or_None).
    """
    errors = {}

    # name
    if len(nom) < 3:
        errors["nom_startup"] = "Startup name must be at least 3 characters."
    invalid = re.sub(r"[A-Za-z0-9\s\-\_]", "", nom)
    if invalid:
        errors["nom_startup"] = errors.get("nom_startup", "") + f' Invalid characters detected: "{invalid}".'

    # category
    if len(cat) < 2:
        errors["category"] = "Category must be at least 2 characters."
    invalid = re.sub(r"[A-Za-z0-9\s\-\_\/]", "", cat)
    if invalid:
        errors["category"] = errors.get("category", "") + f' Invalid characters detected: "{invalid}".'

    # description
    if len(desc) < 20:
        errors["description"] = "Description must be at least 20 characters."

    # funding
    fond_val = None
    try:
        fond_val = float(fond_desire)
        if fond_val <= 0:
            errors["fond_desire"] = "Funding must be greater than 0."
    except Exception:
        errors["fond_desire"] = "Funding must be a valid number."

    return errors, fond_val


def home(request):
    return render(request, 'startup/Frontoffice/index.html')

def base(request):
    return render(request, 'startup/Backoffice/base.html')
def dashboard_startup(request):
    return render(request, 'startup/Backoffice/dashboard_startup.html')
def investmentList(request):
    return render(request, 'startup/Backoffice/investmentList.html')
def startupList(request):
    return render(request, 'startup/Backoffice/startupList.html')

def about(request):
    return render(request, 'about.html')


def instructors(request):
    return render(request, 'instructors.html')

def pricing(request):
    return render(request, 'pricing.html')

def blog(request):
    return render(request, 'blog.html')

def course_details(request):
    return render(request, 'course-details.html')

def instructor_profile(request):
    return render(request, 'instructor-profile.html')

def events(request):
    return render(request, 'events.html')

def blog_details(request):
    return render(request, 'blog-details.html')

def terms(request):
    return render(request, 'terms.html')

def privacy(request):
    return render(request, 'privacy.html')

def error_404(request):
    return render(request, '404.html')

def contact(request):
    return render(request, 'contact.html')

def courses(request):
    startups = Startup.objects.filter(statut='active').order_by('-date_creation')
    paginator = Paginator(startups, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    now = timezone.now().date()

    for startup in page_obj:
        startup.time_since_creation = (now - startup.date_creation).days

    return render(request, 'startup/Frontoffice/startup_list.html', {'page_obj': page_obj, 'now': now})


@login_required
def my_startups(request):
    startups = Startup.objects.filter(founder=request.user)
    return render(request, "startup/Frontoffice/my_startups.html", {
        "startups": startups
    })

@login_required
def delete_startup(request, id):
    startup = get_object_or_404(Startup, id_startup=id, founder=request.user)
    # Only allow deletion if user owns it and hasn't raised funds
    if startup.fond_actuel == 0:
        startup.delete()
        
    else:
        messages.error(request, "Cannot delete startup that has received funding.")
    return redirect('my_startups')

@login_required
def edit_startup(request, id):
    try:
        startup = get_object_or_404(Startup, id_startup=id, founder=request.user)
    except Exception as e:
        messages.error(request, "Startup not found or you don't have permission to edit it.")
        return redirect('my_startups')

    if request.method == 'POST':
        try:
            startup.nom_startup = request.POST.get('nom_startup', '').strip()
            startup.description = request.POST.get('description', '').strip()
            startup.category = request.POST.get('category', '').strip()
            fond_desire = request.POST.get('fond_desire')
            
            if not startup.nom_startup or not startup.description or not startup.category:
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'edit_startup.html', {'startup': startup})
            
            if fond_desire:
                try:
                    startup.fond_desire = float(fond_desire)
                except ValueError:
                    messages.error(request, "Invalid funding amount.")
                    return render(request, 'edit_startup.html', {'startup': startup})

            if request.FILES.get('logo'):
                startup.logo = request.FILES.get('logo')

            startup.save()
            return redirect('my_startups')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'startup/Frontoffice/edit_startup.html', {'startup': startup})

    return render(request, 'startup/Frontoffice/edit_startup.html', {'startup': startup})


@login_required
def edit_startup(request, id):
    startup = get_object_or_404(Startup, id_startup=id, founder=request.user)

    if request.method == 'POST':
        errors = {}

        # Retrieve updated values
        nom = request.POST.get('nom_startup', '').strip()
        desc = request.POST.get('description', '').strip()
        cat = request.POST.get('category', '').strip()
        fond_desire = request.POST.get('fond_desire', '').strip()

        import re

        # -----------------------------
        # VALIDATION : nom_startup
        # -----------------------------
        if len(nom) < 3:
            errors['nom_startup'] = "Startup name must be at least 3 characters."

        invalid = re.sub(r'[A-Za-z0-9\s\-\_]', '', nom)
        if invalid:
            errors['nom_startup'] = errors.get('nom_startup', "") + f' Invalid characters detected: "{invalid}".'

        # -----------------------------
        # VALIDATION : category
        # -----------------------------
        if len(cat) < 2:
            errors['category'] = "Category must be at least 2 characters."

        invalid = re.sub(r'[A-Za-z0-9\s\-\_\/]', '', cat)
        if invalid:
            errors['category'] = errors.get('category', "") + f' Invalid characters detected: "{invalid}".'

        # -----------------------------
        # VALIDATION : description
        # -----------------------------
        if len(desc) < 20:
            errors['description'] = "Description must be at least 20 characters."

        # -----------------------------
        # VALIDATION : funding
        # -----------------------------
        try:
            fond_val = float(fond_desire)
            if fond_val <= 0:
                errors['fond_desire'] = "Funding must be greater than 0."
        except:
            errors['fond_desire'] = "Funding must be a valid number."

        # -----------------------------
        # IF ERRORS → RETURN FORM WITH ERRORS
        # -----------------------------
        if errors:
            # keep user input (not overwriting database yet)
            startup.nom_startup = nom
            startup.description = desc
            startup.category = cat
            startup.fond_desire = fond_desire  

            return render(request, 'startup/Frontoffice/edit_startup.html', {
                'startup': startup,
                'errors': errors
            })

        # -----------------------------
        # NO ERRORS → APPLY CHANGES
        # -----------------------------
        startup.nom_startup = nom
        startup.description = desc
        startup.category = cat
        startup.fond_desire = fond_val

        # Replace logo if new one uploaded
        if request.FILES.get('logo'):
            startup.logo = request.FILES.get('logo')

        startup.save()

        return redirect('my_startups')

    # GET method → just load form
    return render(request, 'startup/Frontoffice/edit_startup.html', {
        'startup': startup
    })

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import Startup
import re


@login_required
def create_startup(request):
    if request.method == 'POST':
        nom = request.POST.get('nom_startup', '').strip()
        desc = request.POST.get('description', '').strip()
        cat = request.POST.get('category', '').strip()
        fond_desire = request.POST.get('fond_desire', '').strip()
        logo = request.FILES.get('logo')
        generated_logo_url = request.POST.get('generated_logo_url', '').strip()

        # Shared validation
        errors, fond_val = _validate_startup_payload(nom, desc, cat, fond_desire)

        # -----------------------------
        # VALIDATION : logo (file)
        # -----------------------------
        if logo:
            ext = logo.name.split('.')[-1].lower()
            if ext not in ['png', 'jpg', 'jpeg', 'webp', 'jfif']:
                errors['logo'] = "Only PNG, JPG, JPEG, JFIF or WEBP are allowed."

        # -----------------------------
        # ERRORS → RETURN FORM
        # -----------------------------
        if errors:
            old_data = {
                'nom_startup': nom,
                'description': desc,
                'category': cat,
                'fond_desire': fond_desire,
            }

            return render(request, 'startup/Frontoffice/create_startup.html', {
                'errors': errors,
                'old': old_data
            })

        # If no uploaded logo but a generated URL is provided, download it
        logo_file = logo
        if not logo_file and generated_logo_url:
            try:
                resp = requests.get(generated_logo_url, timeout=20)
                resp.raise_for_status()
                parsed = urlparse(generated_logo_url)
                filename = os.path.basename(parsed.path) or "generated_logo.webp"
                logo_file = ContentFile(resp.content, name=filename)
            except requests.RequestException:
                # If download fails, we silently continue without a logo
                logo_file = None

        # -----------------------------
        # CREATE STARTUP
        # -----------------------------
        new_startup = Startup.objects.create(
            nom_startup=nom,
            description=desc,
            category=cat,
            fond_desire=fond_val,
            fond_actuel=0,
            date_creation=timezone.now().date(),
            statut='Pending',
            logo=logo_file if logo_file else None,
            founder=request.user
        )

        # -----------------------------
        # ADD FOUNDER TO MEMBERS TABLE
        # -----------------------------
        from StartupMembers.models import StartupMember

        StartupMember.objects.create(
            user=request.user,
            startup=new_startup,  # ✔ correct instance
            role="Founder",
            is_lead=True
        )

        return redirect('startup_list')

    return render(request, 'startup/Frontoffice/create_startup.html')


@login_required
@require_POST
def generate_logo(request):
    """
    AJAX endpoint to call RapidAPI AI logo generator based on a text prompt.
    Returns a list of thumbnail + origin URLs.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        return JsonResponse({"error": "Prompt is required."}, status=400)

    rapidapi_key = getattr(settings, "RAPIDAPI_LOGO_KEY", None) or getattr(
        settings, "RAPIDAPI_FAST_PRICE_KEY", None
    )
    if not rapidapi_key:
        return JsonResponse(
            {"error": "RapidAPI logo key is not configured on the server."},
            status=500,
        )

    url = "https://ai-logo-generator.p.rapidapi.com/aaaaaaaaaaaaaaaaaiimagegenerator/quick.php"
    body = {
        "prompt": prompt,
        "style_id": 28,
        "size": "1-1",
    }
    headers = {
        "content-type": "application/json",
        "x-rapidapi-host": "ai-logo-generator.p.rapidapi.com",
        "x-rapidapi-key": rapidapi_key,
    }

    try:
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return JsonResponse(
            {"error": f"Could not reach logo generator service: {exc}"}, status=502
        )
    except ValueError:
        return JsonResponse(
            {"error": "Unexpected response from logo generator service."}, status=502
        )

    # Expected structure based on your example:
    # {
    #   "code": 200,
    #   "message": "Success",
    #   "result": {
    #     "data": {
    #       "results": [
    #         {"origin": "...", "thumb": "..."},
    #         ...
    #       ]
    #     }
    #   }
    # }
    results = []
    try:
        result_data = data.get("result", {}).get("data", {})
        for item in result_data.get("results", []):
            results.append(
                {
                    "origin": item.get("origin"),
                    "thumb": item.get("thumb") or item.get("origin"),
                }
            )
    except Exception:
        return JsonResponse(
            {"error": "Could not parse logo generator response."}, status=502
        )

    if not results:
        return JsonResponse(
            {"error": "No logos were generated. Please try another description."},
            status=400,
        )

    return JsonResponse({"results": results})


@login_required
@require_POST
def startup_chatbot(request):
    """
    Chatbot endpoint backed by RapidAPI (chatgpt-42).
    It can:
      - create a startup for the current user (with validation)
      - delete one of the user's startups (if allowed)
      - or just chat normally
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    user_message = str(body.get("message", "")).strip()
    if not user_message:
        return JsonResponse({"error": "Message is required."}, status=400)

    api_key = getattr(settings, "RAPIDAPI_CHATGPT42_KEY", None) or getattr(
        settings, "RAPIDAPI_FAST_PRICE_KEY", None
    )
    if not api_key:
        return JsonResponse(
            {"error": "RapidAPI ChatGPT key is not configured on the server."},
            status=500,
        )

    system_prompt = (
        "You are an assistant that helps manage startup records for the current user.\n"
        "You MUST ALWAYS answer by returning a single JSON object with this shape:\n"
        '{ \"action\": \"create_startup\" | \"delete_startup\" | \"chat\",\n'
        '  \"data\": { ... },\n'
        '  \"message\": \"short natural language explanation for the user\" }.\n\n'
        "If the user clearly asks to create a startup, use action \"create_startup\" and "
        'put fields in data: { \"nom_startup\", \"description\", \"category\", \"fond_desire\" }.\n'
        "If the user clearly asks to delete one of their startups, use action \"delete_startup\" and "
        'include either \"startup_id\" or \"startup_name\" in data.\n'
        "In all other cases, use action \"chat\" and put your natural language answer in message.\n"
        "Do NOT include code fences, only raw JSON."
    )

    # Payload shape for MATA G 2.0 endpoint (/matag2)
    payload = {
        "messages": [
            {"role": "user", "content": user_message},
        ],
        "system_prompt": system_prompt,
        "temperature": 0.9,
        "top_k": 5,
        "top_p": 0.9,
        "image": "",
        "max_tokens": 512,
    }
    headers = {
        "content-type": "application/json",
        "x-rapidapi-host": "chatgpt-42.p.rapidapi.com",
        "x-rapidapi-key": api_key,
    }

    try:
        resp = requests.post(
            "https://chatgpt-42.p.rapidapi.com/matag2",
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return JsonResponse(
            {"error": f"Could not reach chatbot service: {exc}"}, status=502
        )
    except ValueError:
        return JsonResponse(
            {"error": "Unexpected response from chatbot service."}, status=502
        )

    # MATA G 2.0 often returns a 'result' field with the text answer.
    # If it's missing or not a string, fall back to stringifying the whole payload
    result_text = data.get("result")
    if not isinstance(result_text, str):
        result_text = json.dumps(data, ensure_ascii=False)

    # Parse the JSON that the chatbot was instructed to return
    try:
        action_obj = json.loads(result_text)
    except json.JSONDecodeError:
        # Fallback: just echo the text as chat
        return JsonResponse(
            {"action": "chat", "message": result_text},
            status=200,
        )

    action = action_obj.get("action") or "chat"
    action_data = action_obj.get("data") or {}
    action_message = action_obj.get("message") or ""

    # --- Handle create_startup ---
    if action == "create_startup":
        nom = str(action_data.get("nom_startup", "")).strip()
        desc = str(action_data.get("description", "")).strip()
        cat = str(action_data.get("category", "")).strip()
        fond_desire = str(action_data.get("fond_desire", "")).strip()

        errors, fond_val = _validate_startup_payload(nom, desc, cat, fond_desire)
        if errors:
            return JsonResponse(
                {
                    "action": "create_startup",
                    "success": False,
                    "errors": errors,
                    "message": "Startup could not be created due to validation errors.",
                },
                status=400,
            )

        startup = Startup.objects.create(
            nom_startup=nom,
            description=desc,
            category=cat,
            fond_desire=fond_val,
            fond_actuel=0,
            date_creation=timezone.now().date(),
            statut="Pending",
            founder=request.user,
        )

        return JsonResponse(
            {
                "action": "create_startup",
                "success": True,
                "startup_id": startup.id_startup,
                "message": action_message or "Startup created successfully.",
            }
        )

    # --- Handle delete_startup ---
    if action == "delete_startup":
        startup_id = action_data.get("startup_id")
        startup_name = action_data.get("startup_name", "").strip() or None

        qs = Startup.objects.filter(founder=request.user)
        target = None
        if startup_id is not None:
            try:
                target = qs.get(id_startup=int(startup_id))
            except (ValueError, Startup.DoesNotExist):
                target = None
        elif startup_name:
            target = qs.filter(nom_startup__iexact=startup_name).first()

        if not target:
            return JsonResponse(
                {
                    "action": "delete_startup",
                    "success": False,
                    "message": "No matching startup found to delete.",
                },
                status=404,
            )

        # Apply same rule as your manual delete: only delete if no funds raised
        if target.fond_actuel != 0:
            return JsonResponse(
                {
                    "action": "delete_startup",
                    "success": False,
                    "message": "Cannot delete a startup that has received funding.",
                },
                status=400,
            )

        target.delete()
        return JsonResponse(
            {
                "action": "delete_startup",
                "success": True,
                "message": action_message
                or f'Startup "{target.nom_startup}" was deleted successfully.',
            }
        )

    # Default: just chat
    return JsonResponse(
        {
            "action": "chat",
            "message": action_message or result_text,
        }
    )

from django.shortcuts import render
from Startup.models import Startup
from Investissement.models import Investissement

def backoffice_dashboard(request):
    total_startups = Startup.objects.count()
    pending_startups = Startup.objects.filter(statut="Pending").count()

    total_invests = Investissement.objects.count()
    pending_invests = Investissement.objects.filter(statut="pending").count()

    return render(request, "startup/Backoffice/dashboard_overview.html", {
        "total_startups": total_startups,
        "pending_startups": pending_startups,
        "total_invests": total_invests,
        "pending_invests": pending_invests,
    })
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test

from Startup.models import Startup
from Investissement.models import Investissement


def admin_only(user):
    return user.is_superuser or user.is_staff


# ----------------------------------------------------------
#   DASHBOARD STARTUP (page principale Backoffice)
# ----------------------------------------------------------

@login_required
@user_passes_test(admin_only)
def dashboard_startup(request):
    from Investissement.models import Investissement
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import timedelta

    # --- STARTUP STATS ---
    total_startups = Startup.objects.count()
    pending_startups = Startup.objects.filter(statut="Pending").count()
    active_startups = Startup.objects.filter(statut="active").count()
    funded_startups = Startup.objects.filter(statut="funded").count()

    # --- INVESTMENT STATS ---
    total_investments = Investissement.objects.count()
    pending_investments = Investissement.objects.filter(statut="pending").count()
    accepted_investments = Investissement.objects.filter(statut="accepted").count()
    total_montant_investi = Investissement.objects.filter(statut="accepted").aggregate(Sum('montant'))['montant__sum'] or 0

    # Startups récentes (5 dernières)
    recent_startups = Startup.objects.select_related('founder').order_by('-date_creation')[:5]

    # Investissements récents (5 derniers)
    recent_investments = Investissement.objects.select_related('startup', 'investor').order_by('-date')[:5]

    context = {
        # --- STARTUP STATS ---
        "total_startups": total_startups,
        "pending_startups": pending_startups,
        "active_startups": active_startups,
        "funded_startups": funded_startups,

        # --- INVESTMENT STATS ---
        "total_investments": total_investments,
        "pending_investments": pending_investments,
        "accepted_investments": accepted_investments,
        "total_montant_investi": total_montant_investi,

        # --- RECENT DATA ---
        "recent_startups": recent_startups,
        "recent_investments": recent_investments,
    }

    top_funded = (
    Startup.objects
    .annotate(total_funds=Sum('investissements__montant'))
    .order_by('-total_funds')[:3]
    )

    top_labels = [s.nom_startup for s in top_funded]
    top_values = [(s.total_funds or 0) for s in top_funded]


    # PIE CHART — STARTUP STATUS BREAKDOWN
    status_counts = (
    Startup.objects.values("statut")
    .annotate(total=models.Count("id_startup"))
    )


    status_labels = [entry['statut'] for entry in status_counts]
    status_values = [entry['total'] for entry in status_counts]

    # Add to context
    context.update({
        "top_labels": top_labels,
        "top_values": top_values,
        "status_labels": status_labels,
        "status_values": status_values,
    })


    return render(request, "startup/Backoffice/dashboard_startup.html", context)


# ----------------------------------------------------------
#   STARTUP LIST PAGE
# ----------------------------------------------------------


from django.db.models import F, FloatField, ExpressionWrapper, Case, When, Value
from .models import Startup

@login_required
@user_passes_test(admin_only)
def startupList(request):
    startups = Startup.objects.all()

    # Add pct_funded to each startup safely
    for s in startups:
        if s.fond_desire and s.fond_desire > 0:
            s.pct_funded = (s.fond_actuel or 0) / s.fond_desire * 100
        else:
            s.pct_funded = 0

    return render(request, "startup/Backoffice/startupList.html", {"startups": startups})
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Startup


from email.mime.image import MIMEImage
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives

@login_required
@user_passes_test(admin_only)
def approve_startup(request, id):
    startup = get_object_or_404(Startup, id_startup=id)

    startup.statut = "active"
    startup.save()

    founder_email = startup.founder.email
    startup_name = startup.nom_startup

    # 1) Prepare CID for the logo (if exists)
    logo_cid = None
    logo_image = None

    if startup.logo and startup.logo.path:
        try:
            with open(startup.logo.path, "rb") as f:
                logo_data = f.read()

            logo_cid = f"startup-logo-{startup.id_startup}"  # any unique string
            logo_image = MIMEImage(logo_data)
            logo_image.add_header("Content-ID", f"<{logo_cid}>")
            logo_image.add_header("Content-Disposition", "inline", filename="logo.png")
        except Exception as e:
            # If anything goes wrong, just skip the logo
            logo_cid = None
            logo_image = None

    # 2) Render HTML with CID
    html_content = render_to_string("emails_startup/startup_approved.html", {
        "startup": startup,
        "logo_cid": logo_cid,
    })

    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject=f"Votre startup '{startup_name}' a été approuvée 🎉",
        body=text_content,
        from_email="karimmlayah14@gmail.com",
        to=[founder_email],
    )

    email.attach_alternative(html_content, "text/html")

    # 3) Attach the logo as inline image
    if logo_image is not None:
        email.attach(logo_image)

    email.send()

    messages.success(request, "Startup approved and email sent to the founder.")
    return redirect('startupList')


def reject_startup(request, id):
    startup = get_object_or_404(Startup, id_startup=id)

    # delete all its investments
    startup.investissements.all().delete()

    # delete startup itself
    startup.delete()

    messages.error(request, "Startup rejected and removed permanently.")
    return redirect('startupList')


# ----------------------------------------------------------
#   INVESTMENT LIST PAGE
# ----------------------------------------------------------

@login_required
@user_passes_test(admin_only)
def investmentList(request):
    investments = Investissement.objects.select_related("startup", "investor").order_by("-date")

    return render(request, "startup/Backoffice/investmentList.html", {
        "investments": investments,
        "pending_count": Investissement.objects.filter(statut="pending").count()
    })

@login_required
@user_passes_test(admin_only)
def investmentList(request):
    investments = Investissement.objects.select_related("startup", "investor").order_by("-date")

    return render(request, "startup/Backoffice/investmentList.html", {
        "investments": investments,
        "pending_count": Investissement.objects.filter(statut="pending").count()
    })


@login_required
@user_passes_test(admin_only)
def approve_investment(request, invest_id):
    investment = get_object_or_404(Investissement, id_invest=invest_id)

    investment.statut = "accepted"
    investment.save()  # triggers your save() logic to add funds

    messages.success(request, "Investment approved!")
    return redirect("investmentList")


@login_required
@user_passes_test(admin_only)
def reject_investment(request, invest_id):
    investment = get_object_or_404(Investissement, id_invest=invest_id)

    investment.statut = "rejected"
    investment.save(update_fields=["statut"])

    messages.error(request, "Investment marked as REJECTED.")
    return redirect("investmentList")


from django.db.models import Sum
from django.db import models
