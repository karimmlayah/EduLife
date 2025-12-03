from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse

from django.conf import settings
import json
import requests
import stripe

from Startup.models import Startup
from .models import Investissement


# Configure Stripe with secret key from settings
stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")


def _validate_investissement_form(data):
    errors = {}
    montant_raw = data.get('montant', '').strip()
    commentaire = data.get('commentaire', '').strip()

    try:
        montant_val = float(montant_raw)
        if montant_val <= 0:
            errors['montant'] = "Investment amount must be greater than 0."
    except (TypeError, ValueError):
        errors['montant'] = "Investment amount must be a valid number."

    if commentaire and len(commentaire) < 10:
        errors['commentaire'] = "Comment must contain at least 10 characters."

    return errors, montant_raw, commentaire

@login_required
def create_investissement(request, startup_id):
    startup = get_object_or_404(Startup, id_startup=startup_id)

    if request.method == 'POST':
        errors, montant_raw, commentaire = _validate_create_form(request.POST)

        if errors:
            return render(request, 'startup/Frontoffice/create_investissement.html', {
                'startup': startup,
                'errors': errors,
                'old': {
                    'montant': montant_raw,
                    'commentaire': commentaire,
                }
            })

        montant_val = float(montant_raw)

        # Create investment in pending state (will be marked accepted on Stripe success)
        investissement = Investissement.objects.create(
            startup=startup,
            investor=request.user,
            montant=montant_val,
            date=timezone.now().date(),
            commentaire=commentaire or None,
            statut='pending'
        )

        # Create Stripe Checkout Session
        try:
            # Stripe expects smallest currency unit (e.g. cents).
            # Business rule: amount in TND is divided by 3 to charge in USD equivalent.
            usd_amount = montant_val / 3.0
            amount_cents = int(round(usd_amount * 100))

            success_url = request.build_absolute_uri(
                reverse('invest_checkout_success')
            ) + f"?invest_id={investissement.id_invest}&session_id={{CHECKOUT_SESSION_ID}}"

            cancel_url = request.build_absolute_uri(
                reverse('invest_checkout_cancel')
            ) + f"?invest_id={investissement.id_invest}"

            checkout_session = stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",  # Adapt if you support another currency
                            "product_data": {
                                "name": f"Investment in {startup.nom_startup}",
                            },
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                success_url=success_url,
                cancel_url=cancel_url,
            )

            return redirect(checkout_session.url, permanent=False)

        except Exception as e:
            # If Stripe fails, keep the investment as pending and show an error
            messages.error(request, f"Error initializing Stripe payment: {e}")
            return redirect('my_investissements')

    return render(request, 'startup/Frontoffice/create_investissement.html', {'startup': startup})


@login_required
def my_investissements(request):
    investissements = (
        Investissement.objects
        .filter(investor=request.user)
        .select_related("startup")  # <-- FIXED
        .order_by('-date')
    )

    return render(request, 'startup/Frontoffice/my_investissements.html', {
        'investissements': investissements
    })


@login_required
def invest_checkout_success(request):
    """
    Called by Stripe after a successful payment.
    Marks the investment as accepted (if still pending).
    """
    invest_id = request.GET.get("invest_id")
    if not invest_id:
        messages.error(request, "Missing investment reference after payment.")
        return redirect('my_investissements')

    investissement = get_object_or_404(
        Investissement,
        id_invest=invest_id,
        investor=request.user
    )

    if investissement.statut == "pending":
        investissement.statut = "accepted"
        investissement.save()  # Triggers startup funds update in model.save()
        messages.success(request, "Your investment has been paid successfully.")
    else:
        messages.info(request, "This investment was already processed.")

    return redirect('my_investissements')


@login_required
def invest_checkout_cancel(request):
    """
    Called by Stripe when the user cancels the payment.
    Keeps the investment in pending state.
    """
    messages.info(request, "Payment was cancelled. Your investment remains pending.")
    return redirect('my_investissements')

@login_required
def edit_investissement(request, invest_id):
    investissement = get_object_or_404(Investissement, id_invest=invest_id, investor=request.user)

    if investissement.statut != 'pending':
        messages.error(request, "Only pending investments can be modified.")
        return redirect('my_investissements')

    if request.method == 'POST':
        original_amount = investissement.montant
        errors, montant_raw, commentaire = _validate_investissement_form(request.POST)

        if errors:
            investissement.montant = montant_raw
            investissement.commentaire = commentaire
            return render(request, 'startup/Frontoffice/edit_investissement.html', {
                'investissement': investissement,
                'errors': errors
            })

        montant_val = float(montant_raw)

        difference = montant_val - original_amount
        if difference != 0:
            startup = investissement.startup
            startup.fond_actuel = (startup.fond_actuel or 0) + difference
            if startup.fond_actuel < 0:
                startup.fond_actuel = 0
            startup.save(update_fields=['fond_actuel'])

        investissement.montant = montant_val
        investissement.commentaire = commentaire or None
        investissement.save(update_fields=['montant', 'commentaire'])

        
        return redirect('my_investissements')

    return render(request, 'startup/Frontoffice/edit_investissement.html', {
        'investissement': investissement
    })


@login_required
def delete_investissement(request, invest_id):
    investissement = get_object_or_404(Investissement, id_invest=invest_id, investor=request.user)

    if request.method != 'POST':
        return redirect('my_investissements')

    if investissement.statut != 'pending':
        messages.error(request, "Only pending investments can be deleted.")
        return redirect('my_investissements')

    startup = investissement.startup
    startup.fond_actuel = (startup.fond_actuel or 0) - investissement.montant
    if startup.fond_actuel < 0:
        startup.fond_actuel = 0
    startup.save(update_fields=['fond_actuel'])

    investissement.delete()

    
    return redirect('my_investissements')

def _validate_investissement_form(data):
    errors = {}
    montant_raw = data.get('montant', '').strip()
    commentaire = data.get('commentaire', '').strip()

    # montant validation...
    try:
        montant_val = float(montant_raw)
        if montant_val <= 0:
            errors['montant'] = "Amount must be greater than 0."
    except:
        errors['montant'] = "Amount must be a valid number."

    # commentaire validation (optional but min length if provided)
    if commentaire:
        if len(commentaire) < 5:
            errors['commentaire'] = "Comment must be at least 5 characters."
        # optional: invalid characters
        import re
        invalid = re.sub(r'[A-Za-z0-9\s\-\_\.\,\!\?]', '', commentaire)
        if invalid:
            errors['commentaire'] = errors.get('commentaire', "") + f' Invalid characters detected: "{invalid}".'

    return errors, montant_raw, commentaire
def _validate_investissement_form(data):
    errors = {}
    montant_raw = data.get('montant', '').strip()
    commentaire = data.get('commentaire', '').strip()

    # Validate montant
    try:
        montant_val = float(montant_raw)
        if montant_val <= 0:
            errors['montant'] = "Amount must be greater than 0."
    except:
        errors['montant'] = "Amount must be a valid number."

    # Validate comment (optional)
    if commentaire:
        if len(commentaire) < 5:
            errors['commentaire'] = "Comment must be at least 5 characters."

        import re
        invalid = re.sub(r'[A-Za-z0-9\s\-\_\.\,\!\?]', "", commentaire)
        if invalid:
            errors['commentaire'] = (
                errors.get('commentaire', "")
                + f' Invalid characters detected: "{invalid}".'
            )

    return errors, montant_raw, commentaire



def _validate_create_investissement_form(data):
    errors = {}
    montant_raw = data.get('montant', '').strip()
    commentaire = data.get('commentaire', '').strip()

    # montant
    try:
        montant_val = float(montant_raw)
        if montant_val <= 0:
            errors['montant'] = "Amount must be greater than 0."
    except:
        errors['montant'] = "Amount must be a valid number."

    # commentaire (optional)
    if commentaire:
        if len(commentaire) < 5:
            errors['commentaire'] = "Comment must be at least 5 characters."

        import re
        invalid = commentaire.replace(" ", "")
        invalid = re.sub(r'[A-Za-z0-9\-\_\.\,\!\?]', "", invalid)

        if invalid:
            errors['commentaire'] = (
                errors.get('commentaire', "") +
                f' Invalid characters detected: "{invalid}".'
            )

    return errors, montant_raw, commentaire

def _validate_create_form(data):
    errors = {}
    montant_raw = data.get('montant', '').strip()
    commentaire = data.get('commentaire', '').strip()

    # montant validation
    try:
        montant_val = float(montant_raw)
        if montant_val <= 0:
            errors['montant'] = "Amount must be greater than 0."
    except:
        errors['montant'] = "Amount must be a valid number."

    # commentaire validation
    comment_errors = []   # ⭐ collect multiple errors

    if commentaire:
        if len(commentaire) < 10:
            comment_errors.append("Comment must be at least 10 characters.")

        import re
        cleaned = commentaire.replace(" ", "")
        import re
        invalid = re.sub(r'[A-Za-z0-9\-\_\.\,\!\?]', '', cleaned)


        if invalid:
            comment_errors.append(f'Invalid characters detected: "{invalid}".')

    if comment_errors:
        errors['commentaire'] = " ".join(comment_errors)

    return errors, montant_raw, commentaire


@login_required
@require_POST
def convert_currency(request):
    """
    AJAX endpoint used by the investment form to convert an amount
    from one currency to another using the RapidAPI
    `currency-converter18.p.rapidapi.com` service.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    amount_raw = str(payload.get('amount', '')).strip()
    from_currency = str(payload.get('from_currency', '')).upper().strip()
    to_currency = str(payload.get('to_currency', '')).upper().strip()

    # Basic validation
    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Amount must be a number greater than 0.'}, status=400)

    if not from_currency or not to_currency:
        return JsonResponse({'error': 'Both source and target currencies are required.'}, status=400)

    rapidapi_key = getattr(settings, 'RAPIDAPI_FAST_PRICE_KEY', None)
    if not rapidapi_key:
        return JsonResponse(
            {'error': 'RapidAPI key is not configured on the server.'},
            status=500
        )

    url = "https://currency-converter18.p.rapidapi.com/api/v1/convert"
    params = {
        "from": from_currency,
        "to": to_currency,
        "amount": str(amount),
    }
    headers = {
        "x-rapidapi-host": "currency-converter18.p.rapidapi.com",
        "x-rapidapi-key": rapidapi_key,
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return JsonResponse(
            {'error': f'Could not reach conversion service: {exc}'},
            status=502
        )
    except ValueError:
        return JsonResponse(
            {'error': 'Unexpected response from conversion service.'},
            status=502
        )

    result = data.get("result") or {}
    if not result:
        # Fallback: unexpected format
        return JsonResponse(
            {'error': 'Unexpected data format from conversion service.'},
            status=502
        )

    # Expected format (per your example):
    # {
    #   "success": true,
    #   "validationMessage": [],
    #   "result": {
    #     "from": "EUR",
    #     "to": "KWD",
    #     "amountToConvert": 12,
    #     "convertedAmount": 4.27...
    #   }
    # }
    try:
        converted_amount = float(result.get("convertedAmount"))
        amount_to_convert = float(result.get("amountToConvert", amount))
    except (TypeError, ValueError):
        return JsonResponse(
            {'error': 'Invalid numeric values from conversion service.'},
            status=502
        )

    return JsonResponse({
        'amount': amount_to_convert,
        'from_currency': result.get("from", from_currency),
        'to_currency': result.get("to", to_currency),
        'rate': None,
        'converted_amount': converted_amount,
    })
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.shortcuts import get_object_or_404

from django.template.loader import render_to_string

from fpdf import FPDF
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from Investissement.models import Investissement

def generate_receipt(request, id):
    investissement = get_object_or_404(Investissement, id_invest=id)
    startup = investissement.startup
    investor = investissement.investor
    founder = startup.founder

    pdf = FPDF()
    pdf.add_page()

    # Brand colors
    orange = (248, 117, 0)
    blue = (23, 43, 77)
    dark = (40, 40, 40)

    # Left orange bar
    pdf.set_fill_color(*orange)
    pdf.rect(0, 0, 7, 297, 'F')

    # Top blue bar
    pdf.set_fill_color(*blue)
    pdf.rect(0, 10, 210, 30, 'F')

    # Title
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 20)
    pdf.set_xy(0, 18)
    pdf.cell(0, 10, "Investment Receipt", 0, 1, "C")

    # Decorative square
    pdf.set_fill_color(*orange)
    pdf.rect(185, 15, 12, 12, 'F')

    # Startup logo
    if startup.logo:
        pdf.image(startup.logo.path, 15, 50, 35)

    # Blue square
    pdf.set_fill_color(*blue)
    pdf.rect(165, 50, 10, 10, 'F')

    # --- MAIN INFO BOX ---
    pdf.set_draw_color(*blue)
    pdf.rect(10, 90, 190, 85)

    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(*blue)
    pdf.set_xy(18, 98)
    pdf.cell(0, 10, "Investment Information", 0, 1)

# Row spacing
    line_height = 9
    start_y = 113

    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(0, 0, 0)

    rows = [
        ("Startup", startup.nom_startup),
        ("Investor", investor.username),
        ("Founder", founder.username),
        ("Date", str(investissement.date)),
        ("Status", investissement.statut.capitalize()),
    ]

    for label, value in rows:
        pdf.set_xy(20, start_y)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(50, line_height, f"{label}:", 0, 0)

        pdf.set_font("Arial", "", 12)
        pdf.cell(0, line_height, value, 0, 1)

        start_y += line_height + 2   # more spacing

    # Amount
    pdf.set_font("Arial", "B", 15)
    pdf.set_text_color(*orange)
    pdf.set_xy(120, 155)
    pdf.cell(0, 10, f"Amount: {investissement.montant} TND", 0, 1, 'R')

    # Signature
    pdf.set_xy(130, 200)
    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(*dark)
    pdf.cell(0, 10, "Authorized Signature:", 0, 1, "R")
    pdf.line(150, 215, 200, 215)

    # Footer bar
    pdf.set_fill_color(*blue)
    pdf.rect(0, 265, 210, 10, 'F')

    # Thank you
    pdf.set_xy(130, 250)
    pdf.set_font("Arial", "I", 12)
    pdf.set_text_color(*dark)
    pdf.cell(0, 10, "Thank you for supporting EduLife Startups!", 0, 1, "R")

    # --- Export PDF correctly ---
    # --- CREATE RAW PDF BYTES SAFELY ---
    raw_pdf = pdf.output(dest='S')

# FPDF may return str, bytes, or bytearray depending on version
    if isinstance(raw_pdf, str):
        pdf_bytes = raw_pdf.encode('latin-1')
    elif isinstance(raw_pdf, bytearray):
        pdf_bytes = bytes(raw_pdf)
    else:
        pdf_bytes = raw_pdf

# --- SEND RESPONSE ---
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="receipt_{id}.pdf"'
    return response


