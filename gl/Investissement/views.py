from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from Startup.models import Startup
from .models import Investissement


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
            return render(request, 'Frontoffice/create_investissement.html', {
                'startup': startup,
                'errors': errors,
                'old': {
                    'montant': montant_raw,
                    'commentaire': commentaire,
                }
            })

        montant_val = float(montant_raw)

        Investissement.objects.create(
            startup=startup,
            investor=request.user,
            montant=montant_val,
            date=timezone.now().date(),
            commentaire=commentaire or None,
            statut='pending'
        )
        return redirect('my_investissements')

    return render(request, 'Frontoffice/create_investissement.html', {'startup': startup})


@login_required
def my_investissements(request):
    investissements = (
        Investissement.objects
        .filter(investor=request.user)
        .select_related("startup")  # <-- FIXED
        .order_by('-date')
    )

    return render(request, 'Frontoffice/my_investissements.html', {
        'investissements': investissements
    })

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
            return render(request, 'Frontoffice/edit_investissement.html', {
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

    return render(request, 'Frontoffice/edit_investissement.html', {
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
