from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Startup
import Startup.templatetags.startup_extras as startup_tags


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
        errors = {}

        nom = request.POST.get('nom_startup', '').strip()
        desc = request.POST.get('description', '').strip()
        cat = request.POST.get('category', '').strip()
        fond_desire = request.POST.get('fond_desire', '').strip()
        logo = request.FILES.get('logo')

        import re

        # -----------------------------
        # VALIDATION : nom_startup
        # -----------------------------
        if len(nom) < 3:
            errors['nom_startup'] = "Startup name must be at least 3 characters."

        invalid = re.sub(r'[A-Za-z0-9\s\-\_]', '', nom)
        if invalid:
            errors['nom_startup'] = errors.get('nom_startup', "") + f' Invalid characters detected: \"{invalid}\".'

        # -----------------------------
        # VALIDATION : category
        # -----------------------------
        if len(cat) < 2:
            errors['category'] = "Category must be at least 2 characters."

        invalid = re.sub(r'[A-Za-z0-9\s\-\_\/]', '', cat)
        if invalid:
            errors['category'] = errors.get('category', "") + f' Invalid characters detected: \"{invalid}\".'

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
        # VALIDATION : logo
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
                'fond_desire': fond_desire
            }

            return render(request, 'startup/Frontoffice/create_startup.html', {
                'errors': errors,
                'old': old_data
            })

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
            logo=logo,
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

from django.shortcuts import render
from Startup.models import Startup
from Investissement.models import Investissement

def backoffice_dashboard(request):
    total_startups = Startup.objects.count()
    pending_startups = Startup.objects.filter(statut="pending").count()

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
    return user.is_authenticated and (user.is_superuser or user.is_staff or (hasattr(user, 'role') and user.role == 'ADMIN'))


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
    pending_startups = Startup.objects.filter(statut="pending").count()
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

@login_required
@user_passes_test(admin_only)


def approve_startup(request, id):
    startup = get_object_or_404(Startup, id_startup=id)
    startup.statut = "active"
    startup.save()
    messages.success(request, "Startup approved.")
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
