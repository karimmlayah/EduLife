"""
URL configuration for gl project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
    1. Add an import:  from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from LogementApp.views import dashboard as admin_dashboard_view, argon_page, tables, dashboard_logements, manage_logements, approve_logement, reject_logement, admin_edubot, admin_edubox
from EventApp import views
from EventApp.views import dashboard_events
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from ReservationApp.views import mes_reservations_passager



from django.shortcuts import redirect

# IMPORTS DES RÉSERVATIONS (IMPORTANT : AVANT urlpatterns)
from gl.views import (
    mes_reservations,
    reservation_accept,
    reservation_reject,
    approver_offre,
    rejeter_offre,
)
from gl import views as gl_views
from CovoiturageApp import views as covoiturage_views

def redirect_to_dashboard(request):
    return redirect('dashboard')


# Vues pour toutes les pages du template
def index(request):
    return render(request, 'stages/Frontoffice/index.html')

def about(request):
    return render(request, 'stages/Frontoffice/about.html')

def internships(request):
    from offreStage.models import OffreStage
    
    # Récupérer le paramètre de durée depuis l'URL
    duree_filter = request.GET.get('duree', None)
    
    # Base query pour les offres visibles
    offres_visibles = OffreStage.objects.filter(visibilite=True)
    
    # Filtrer par durée si un filtre est sélectionné
    if duree_filter:
        try:
            # Format attendu: "more_than_3" ou "less_than_3" (en mois, convertis en semaines)
            if duree_filter.startswith('more_than_'):
                mois = int(duree_filter.replace('more_than_', ''))
                semaines = mois * 4  # Approximation: 1 mois = 4 semaines
                offres_visibles = offres_visibles.filter(duree__gte=semaines)
            elif duree_filter.startswith('less_than_'):
                mois = int(duree_filter.replace('less_than_', ''))
                semaines = mois * 4
                offres_visibles = offres_visibles.filter(duree__lte=semaines)
        except Exception as e:
            print(f"Erreur lors du filtrage par durée: {e}")
            pass
    
    offres_visibles = offres_visibles.order_by('-date_publication', '-id_offre')
    
    # Convertir le QuerySet en liste pour éviter les problèmes de lazy evaluation
    offres_list = list(offres_visibles)
    
    # Debug: vérifier le nombre d'offres
    print(f"Nombre d'offres visibles: {len(offres_list)}")
    print(f"Total offres dans la base: {OffreStage.objects.count()}")
    print(f"Offres avec visibilite=True: {OffreStage.objects.filter(visibilite=True).count()}")
    
    context = {
        'offres': offres_list,
        'duree_filter': duree_filter,
    }
    return render(request, 'stages/Frontoffice/schedule.html', context)

def postuler(request):
    from postulation.forms import PostulationForm
    from django.contrib import messages
    from django.shortcuts import redirect
    
    # Rediriger les requêtes GET vers internships
    if request.method != 'POST':
        return redirect('internships')
    
    form = PostulationForm(request.POST, request.FILES)
    if form.is_valid():
        postulation = form.save()
        # Sauvegarder l'email dans la session
        request.session['user_email'] = postulation.email
        messages.success(request, 'Your application has been submitted successfully!')
        return redirect('my_applications')
    else:
        # En cas d'erreur, rediriger vers internships avec les erreurs en session
        messages.error(request, 'Please check your form and try again.')
        # Stocker les erreurs dans la session pour les afficher
        request.session['form_errors'] = form.errors.as_json()
        return redirect('internships')

def contact(request):
    return render(request, 'stages/Frontoffice/contact.html')

def dashboard(request):
    from offreStage.models import OffreStage
    from postulation.models import Postulation
    from entretien.models import Entretien
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    # Dates pour les calculs
    maintenant = timezone.now()
    date_semaine = maintenant - timedelta(days=7)
    date_mois = maintenant - timedelta(days=30)
    
    # Statistiques des offres
    total_offres = OffreStage.objects.filter(visibilite=True).count()
    nouvelles_offres = OffreStage.objects.filter(visibilite=True, date_publication__gte=date_semaine).count()
    offres_disponibles = OffreStage.objects.filter(visibilite=True, etat='disponible').count()
    offres_indisponibles = OffreStage.objects.filter(visibilite=True, etat='indisponible').count()
    
    # Statistiques des postulations
    total_postulations = Postulation.objects.count()
    nouvelles_postulations = Postulation.objects.filter(date_postulation__gte=date_semaine).count()
    postulations_en_attente = Postulation.objects.filter(statut='en_attente').count()
    postulations_acceptees = Postulation.objects.filter(statut='acceptee').count()
    postulations_refusees = Postulation.objects.filter(statut='refusee').count()
    
    # Nouveaux candidats uniques cette semaine
    nouveaux_candidats = Postulation.objects.filter(date_postulation__gte=date_semaine).values('email').distinct().count()
    
    # Taux de réponse (acceptées / total)
    taux_reponse = round((postulations_acceptees / total_postulations * 100) if total_postulations > 0 else 0, 1)
    
    # Statistiques des entretiens
    total_entretiens = Entretien.objects.count()
    entretiens_planifies = Entretien.objects.filter(statut='planifie').count()
    entretiens_effectues = Entretien.objects.filter(statut='effectue').count()
    
    # Postulations par statut (pour le graphique)
    postulations_par_statut = {
        'en_attente': postulations_en_attente,
        'acceptee': postulations_acceptees,
        'refusee': postulations_refusees
    }
    
    # Récupérer les dernières postulations
    postulations = Postulation.objects.select_related('offre').order_by('-date_postulation')[:10]
    
    # Top 5 offres les plus demandées
    top_offres = OffreStage.objects.annotate(
        nb_postulations=Count('postulations')
    ).filter(visibilite=True).order_by('-nb_postulations')[:5]
    
    context = {
        'total_offres': total_offres,
        'nouvelles_offres': nouvelles_offres,
        'offres_disponibles': offres_disponibles,
        'offres_indisponibles': offres_indisponibles,
        'total_postulations': total_postulations,
        'nouvelles_postulations': nouvelles_postulations,
        'postulations_en_attente': postulations_en_attente,
        'postulations_acceptees': postulations_acceptees,
        'postulations_refusees': postulations_refusees,
        'nouveaux_candidats': nouveaux_candidats,
        'taux_reponse': taux_reponse,
        'total_entretiens': total_entretiens,
        'entretiens_planifies': entretiens_planifies,
        'entretiens_effectues': entretiens_effectues,
        'postulations_par_statut': postulations_par_statut,
        'postulations': postulations,
        'top_offres': top_offres,
    }
    
    return render(request, 'stages/Backoffice/dashboard.html', context)

def offres_stage(request):
    from offreStage.models import OffreStage
    from offreStage.forms import OffreStageForm
    from django.shortcuts import redirect, get_object_or_404
    from django.db.models import Q
    from django.contrib import messages
    
    offres = OffreStage.objects.all()
    
    # Recherche
    search_query = request.GET.get('search', '')
    if search_query:
        offres = offres.filter(
            Q(titre__icontains=search_query) |
            Q(domaine__icontains=search_query) |
            Q(lieu__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filtres
    visibilite_filter = request.GET.get('visibilite', '')
    if visibilite_filter == 'visible':
        offres = offres.filter(visibilite=True)
    elif visibilite_filter == 'masquee':
        offres = offres.filter(visibilite=False)
    
    etat_filter = request.GET.get('etat', '')
    if etat_filter:
        offres = offres.filter(etat=etat_filter)
    
    domaine_filter = request.GET.get('domaine', '')
    if domaine_filter:
        offres = offres.filter(domaine=domaine_filter)
    
    # Tri
    sort_by = request.GET.get('sort', '-id_offre')
    if sort_by == 'titre':
        offres = offres.order_by('titre')
    elif sort_by == '-titre':
        offres = offres.order_by('-titre')
    elif sort_by == 'date':
        offres = offres.order_by('date_publication')
    elif sort_by == '-date':
        offres = offres.order_by('-date_publication')
    elif sort_by == 'remuneration':
        offres = offres.order_by('remuneration')
    elif sort_by == '-remuneration':
        offres = offres.order_by('-remuneration')
    elif sort_by == 'duree':
        offres = offres.order_by('duree')
    elif sort_by == '-duree':
        offres = offres.order_by('-duree')
    else:
        offres = offres.order_by('-id_offre')
    
    if request.method == 'POST':
        if 'delete' in request.POST:
            offre_id = request.POST.get('delete')
            offre = get_object_or_404(OffreStage, id_offre=offre_id)
            offre_titre = offre.titre
            offre.delete()
            messages.success(request, f'Offer "{offre_titre}" has been deleted successfully.')
            return redirect('offres_stage')
        else:
            offre_id = request.POST.get('offre_id')
            if offre_id:
                offre = get_object_or_404(OffreStage, id_offre=offre_id)
                form = OffreStageForm(request.POST, request.FILES, instance=offre)
            else:
                form = OffreStageForm(request.POST, request.FILES)
            
            if form.is_valid():
                saved_offre = form.save()
                if offre_id:
                    messages.success(request, f'Offer "{saved_offre.titre}" has been updated successfully.')
                else:
                    messages.success(request, f'Offer "{saved_offre.titre}" has been created successfully.')
                return redirect('offres_stage')
            else:
                # Debug: afficher les erreurs du formulaire
                print("Erreurs du formulaire:", form.errors)
                print("Données reçues:", request.POST)
    else:
        offre_id = request.GET.get('edit')
        if offre_id:
            offre = get_object_or_404(OffreStage, id_offre=offre_id)
            form = OffreStageForm(instance=offre)
        else:
            form = OffreStageForm()
    
    # Récupérer les domaines uniques pour le filtre
    domaines = OffreStage.objects.values_list('domaine', flat=True).distinct().order_by('domaine')
    etats = OffreStage.objects.values_list('etat', flat=True).distinct().order_by('etat')
    
    context = {
        'offres': offres,
        'form': form,
        'editing': 'edit' in request.GET,
        'search_query': search_query,
        'visibilite_filter': visibilite_filter,
        'etat_filter': etat_filter,
        'domaine_filter': domaine_filter,
        'sort_by': sort_by,
        'domaines': domaines,
        'etats': etats,
    }
    return render(request, 'stages/Backoffice/offres_stage.html', context)

def postulations(request):
    from postulation.models import Postulation
    from django.db.models import Q
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    
    postulations = Postulation.objects.select_related('offre').all()
    
    # Recherche
    search_query = request.GET.get('search', '')
    if search_query:
        postulations = postulations.filter(
            Q(email__icontains=search_query) |
            Q(offre__titre__icontains=search_query) |
            Q(lettre_motivation__icontains=search_query)
        )
    
    # Filtre par statut
    statut_filter = request.GET.get('statut', '')
    if statut_filter:
        postulations = postulations.filter(statut=statut_filter)
    
    # Tri
    sort_by = request.GET.get('sort', '-date_postulation')
    if sort_by == 'date':
        postulations = postulations.order_by('date_postulation')
    elif sort_by == '-date':
        postulations = postulations.order_by('-date_postulation')
    elif sort_by == 'email':
        postulations = postulations.order_by('email')
    elif sort_by == '-email':
        postulations = postulations.order_by('-email')
    elif sort_by == 'offre':
        postulations = postulations.order_by('offre__titre')
    elif sort_by == '-offre':
        postulations = postulations.order_by('-offre__titre')
    else:
        postulations = postulations.order_by('-date_postulation')
    
    if request.method == 'POST':
        if 'accepter' in request.POST:
            postulation_id = request.POST.get('accepter')
            postulation = get_object_or_404(Postulation, id_postulation=postulation_id)
            postulation.statut = 'acceptee'
            postulation.save()
            messages.success(request, f'Application from {postulation.email} has been accepted successfully.')
            return redirect('postulations')
        elif 'supprimer' in request.POST:
            postulation_id = request.POST.get('supprimer')
            postulation = get_object_or_404(Postulation, id_postulation=postulation_id)
            postulation_email = postulation.email
            postulation.delete()
            messages.success(request, f'Application from {postulation_email} has been deleted successfully.')
            return redirect('postulations')
    
    context = {
        'postulations': postulations,
        'search_query': search_query,
        'statut_filter': statut_filter,
        'sort_by': sort_by,
    }
    return render(request, 'stages/Backoffice/postulations.html', context)

def entretiens(request):
    from entretien.views import liste_entretiens
    return liste_entretiens(request)


# --- CALENDAR DASHBOARD VIEWS (STUB IMPLEMENTATIONS) ---

def calendar(request):
    """
    Simple placeholder view for the internship dashboard calendar.
    Replace with real implementation when ready.
    """
    return HttpResponse("Calendar dashboard view not yet implemented.")


def calendar_api_events(request):
    """
    Placeholder API returning an empty list of events.
    """
    return JsonResponse([], safe=False)


def calendar_api_accepted_applications(request):
    """
    Placeholder API returning an empty list of accepted applications.
    """
    return JsonResponse([], safe=False)


def calendar_api_create_event(request):
    """
    Placeholder API for creating an event.
    """
    return JsonResponse({"detail": "Create event API not yet implemented."}, status=501)


def calendar_api_update_event_date(request, event_id):
    """
    Placeholder API for updating an event date.
    """
    return JsonResponse({"detail": "Update event date API not yet implemented."}, status=501)


def calendar_api_update_event(request, event_id):
    """
    Placeholder API for updating an event.
    """
    return JsonResponse({"detail": "Update event API not yet implemented."}, status=501)


def calendar_api_delete_event(request, event_id):
    """
    Placeholder API for deleting an event.
    """
    return JsonResponse({"detail": "Delete event API not yet implemented."}, status=501)

def my_applications(request):
    from postulation.models import Postulation
    from django.shortcuts import redirect
    
    # Si POST, sauvegarder l'email et rediriger vers GET
    if request.method == 'POST' and 'email' in request.POST:
        user_email = request.POST.get('email')
        request.session['user_email'] = user_email
        return redirect('my_applications')
    
    # Récupérer l'email depuis la session
    user_email = request.session.get('user_email', None)
    
    mes_postulations = []
    if user_email:
        mes_postulations = Postulation.objects.filter(email=user_email).select_related('offre').order_by('-date_postulation')
    
    context = {
        'user_email': user_email,
        'mes_postulations': mes_postulations,
    }
    return render(request, 'stages/Frontoffice/my_applications.html', context)

def my_interviews(request):
    from entretien.models import Entretien
    from django.shortcuts import redirect
    
    # Si POST, sauvegarder l'email et rediriger vers GET
    if request.method == 'POST' and 'email' in request.POST:
        user_email = request.POST.get('email')
        request.session['user_email'] = user_email
        return redirect('my_interviews')
    
    # Récupérer l'email depuis la session
    user_email = request.session.get('user_email', None)
    
    mes_entretiens = []
    if user_email:
        mes_entretiens = Entretien.objects.filter(postulation__email=user_email).select_related('postulation__offre').order_by('-date_entretien')
    
    context = {
        'user_email': user_email,
        'mes_entretiens': mes_entretiens,
    }
    return render(request, 'stages/Frontoffice/my_interviews.html', context)

def startup(request):
    return render(request, 'stages/Backoffice/startup.html')

def housing(request):
    return render(request, 'stages/Backoffice/housing.html')

def ride_sharing(request):
    return render(request, 'stages/Backoffice/ride_sharing.html')

def events(request):
    return render(request, 'stages/Backoffice/events.html')

def my_favoris(request):
    """Vue pour afficher les offres favorites de l'utilisateur"""
    from offreStage.models import Favori
    from django.shortcuts import redirect
   
    # Si l'utilisateur n'est pas connecté, rediriger vers la page de login ou afficher un message
    if not request.user.is_authenticated:
        # Rediriger vers la page internships avec un message
        from django.contrib import messages
        messages.info(request, 'Vous devez être connecté pour voir vos favoris.')
        return redirect('internships')
   
    # Récupérer les favoris de l'utilisateur
    favoris = Favori.objects.filter(user=request.user).select_related('offre').order_by('-date_ajout')
   
    context = {
        'favoris': favoris,
    }
    return render(request, 'stages/Frontoffice/my_favoris.html', context)

def generate_cv(request):
    """Vue pour afficher le formulaire CV et générer le PDF"""
    from offreStage.models import CVData
    from offreStage.forms import CVForm
    from django.shortcuts import redirect
    from django.contrib import messages
   
    # Si l'utilisateur n'est pas connecté, rediriger
    if not request.user.is_authenticated:
        messages.info(request, 'Vous devez être connecté pour générer votre CV.')
        return redirect('internships')
   
    # Récupérer ou créer les données CV
    cv_data, created = CVData.objects.get_or_create(user=request.user)
   
    # Si c'est une requête POST pour générer le PDF
    if request.method == 'POST' and 'generate_pdf' in request.POST:
        # Sauvegarder d'abord les données du formulaire avant de générer le PDF
        form = CVForm(request.POST, instance=cv_data)
        if form.is_valid():
            cv_data = form.save()  # Récupérer l'instance sauvegardée
            # Recharger les données depuis la base de données pour être sûr
            cv_data.refresh_from_db()
        # Vérifier que reportlab est installé
        try:
            import reportlab
        except ImportError:
            messages.error(request, 'ReportLab n\'est pas installé. Veuillez installer reportlab: pip install reportlab')
            return redirect('generate_cv')
        return generate_cv_pdf(request, cv_data)
   
    # Sinon, afficher/éditer le formulaire
    if request.method == 'POST':
        form = CVForm(request.POST, instance=cv_data)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vos données CV ont été sauvegardées avec succès!')
            return redirect('generate_cv')
    else:
        # Pré-remplir avec les données de CustomUser si disponibles
        initial_data = {
            'full_name': cv_data.full_name or f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': cv_data.email or request.user.email,
            'phone': cv_data.phone or request.user.phone or '',
            'address': cv_data.address or request.user.location or '',
            'linkedin': cv_data.linkedin or '',
            'github': cv_data.github or '',
            'website': cv_data.website or '',
            'professional_summary': cv_data.professional_summary or request.user.bio or '',
        }
        form = CVForm(instance=cv_data, initial=initial_data)
   
    import json
    context = {
        'form': form,
        'cv_data': cv_data,
        'skills_json': json.dumps(cv_data.skills or []),
        'languages_json': json.dumps(cv_data.languages or []),
        'certifications_json': json.dumps(cv_data.certifications or []),
    }
    return render(request, 'stages/Frontoffice/generate_cv.html', context)

def generate_cv_pdf(request, cv_data):
    """Génère le PDF du CV"""
    from django.http import HttpResponse
    from django.contrib import messages
    from django.shortcuts import redirect
   
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.platypus.flowables import HRFlowable
    except ImportError as e:
        messages.error(request, f'ReportLab n\'est pas installé. Veuillez installer reportlab: pip install reportlab. Erreur: {str(e)}')
        return redirect('generate_cv')
   
    from io import BytesIO
    import json
   
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.7*inch, leftMargin=0.7*inch, topMargin=0.6*inch, bottomMargin=0.6*inch)
   
    # Styles améliorés et créatifs
    styles = getSampleStyleSheet()
   
    # Style pour le titre principal (nom) - orange comme le formulaire
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=32,
        textColor=colors.HexColor('#ff6b35'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=38
    )
   
    # Style pour les sous-titres de section - orange comme le formulaire
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#ff6b35'),
        spaceAfter=8,
        spaceBefore=0,
        fontName='Helvetica-Bold',
        leftIndent=0,
        rightIndent=0,
        leading=20
    )
   
    # Style pour le texte normal
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=13,
        leading=20,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=10,
        leftIndent=0,
        rightIndent=0
    )
   
    # Style pour les informations de contact
    contact_style = ParagraphStyle(
        'ContactStyle',
        parent=styles['Normal'],
        fontSize=12,
        leading=18,
        textColor=colors.HexColor('#555555'),
        alignment=TA_CENTER,
        spaceAfter=8
    )
   
    # Style pour les éléments de liste (compétences, langues)
    list_item_style = ParagraphStyle(
        'ListItemStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        textColor=colors.HexColor('#444444'),
        leftIndent=20,
        bulletIndent=8,
        spaceAfter=4
    )
   
    # Contenu du CV avec design inspiré du formulaire
    story = []
   
    # Nom avec style orange comme le formulaire
    full_name = (cv_data.full_name or request.user.username or "CV").replace('<', '&lt;').replace('>', '&gt;')
    story.append(Paragraph(full_name, title_style))
    story.append(Spacer(1, 0.3*inch))
   
    # Informations de contact avec liens cliquables
    contact_parts = []
    if cv_data.email:
        email_link = f'<link href="mailto:{cv_data.email}" color="#ff6b35"><u>{cv_data.email}</u></link>'
        contact_parts.append(email_link)
    if cv_data.phone:
        phone_link = f'<link href="tel:{cv_data.phone}" color="#ff6b35"><u>{cv_data.phone}</u></link>'
        contact_parts.append(phone_link)
    if cv_data.address:
        contact_parts.append(cv_data.address)
   
    if contact_parts:
        contact_text = '  •  '.join(contact_parts)
        story.append(Paragraph(contact_text, contact_style))
        story.append(Spacer(1, 0.1*inch))
   
    # Liens sociaux avec liens cliquables
    links_parts = []
    # Vérifier si les champs existent et ne sont pas vides (chaîne vide ou None)
    if cv_data.linkedin and cv_data.linkedin.strip():
        linkedin_url = cv_data.linkedin.strip()
        if not linkedin_url.startswith('http'):
            linkedin_url = f'https://{linkedin_url}'
        linkedin_link = f'<link href="{linkedin_url}" color="#ff6b35"><u>LinkedIn</u></link>'
        links_parts.append(linkedin_link)
    if cv_data.github and cv_data.github.strip():
        github_url = cv_data.github.strip()
        if not github_url.startswith('http'):
            github_url = f'https://{github_url}'
        github_link = f'<link href="{github_url}" color="#ff6b35"><u>GitHub</u></link>'
        links_parts.append(github_link)
    if cv_data.website and cv_data.website.strip():
        website_url = cv_data.website.strip()
        if not website_url.startswith('http'):
            website_url = f'https://{website_url}'
        website_link = f'<link href="{website_url}" color="#ff6b35"><u>Website</u></link>'
        links_parts.append(website_link)
   
    if links_parts:
        links_text = '  •  '.join(links_parts)
        story.append(Paragraph(links_text, contact_style))
        story.append(Spacer(1, 0.35*inch))
   
    # Résumé professionnel avec design inspiré du formulaire
    if cv_data.professional_summary:
        # Section avec fond gris clair comme le formulaire
        summary_section = Table([
            [
                Paragraph("<font color='#ff6b35'><b>PROFESSIONAL SUMMARY</b></font>", heading_style)
            ],
            [
                Paragraph('', normal_style)  # Ligne de séparation orange
            ],
            [
                Paragraph(cv_data.professional_summary.replace('\n', '<br/>'), normal_style)
            ]
        ], colWidths=[7.2*inch])
       
        summary_section.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),  # Fond gris clair
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('RIGHTPADDING', (0, 0), (-1, -1), 20),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 1), (-1, 1), 2, colors.HexColor('#ff6b35')),  # Bordure orange
            ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
        ]))
       
        story.append(summary_section)
        story.append(Spacer(1, 0.3*inch))
   
    # Compétences avec design inspiré du formulaire (badges)
    if cv_data.skills:
        # S'assurer que skills est une liste
        if isinstance(cv_data.skills, str):
            try:
                skills_list = json.loads(cv_data.skills)
            except:
                skills_list = [cv_data.skills]
        elif isinstance(cv_data.skills, list):
            skills_list = cv_data.skills
        else:
            skills_list = [str(cv_data.skills)]
       
        if skills_list:
            # Créer une section avec fond gris clair
            skills_data = [[Paragraph("<font color='#ff6b35'><b>SKILLS</b></font>", heading_style)]]
            skills_data.append([Paragraph('', normal_style)])  # Ligne de séparation
           
            # Créer des badges pour chaque compétence
            badges_text = '  '.join([f"<b>{str(s)}</b>" for s in skills_list if s])
            skills_data.append([Paragraph(badges_text, normal_style)])
           
            skills_section = Table(skills_data, colWidths=[7.2*inch])
            skills_section.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),  # Fond gris clair
                ('TOPPADDING', (0, 0), (-1, -1), 20),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),
                ('RIGHTPADDING', (0, 0), (-1, -1), 20),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (0, 1), (-1, 1), 2, colors.HexColor('#ff6b35')),  # Bordure orange
                ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
            ]))
            story.append(skills_section)
            story.append(Spacer(1, 0.3*inch))
   
   
   
    # Langues avec design inspiré du formulaire (badges)
    if cv_data.languages:
        # S'assurer que languages est une liste
        if isinstance(cv_data.languages, str):
            try:
                lang_list = json.loads(cv_data.languages)
            except:
                lang_list = [cv_data.languages]
        elif isinstance(cv_data.languages, list):
            lang_list = cv_data.languages
        else:
            lang_list = [str(cv_data.languages)]
       
        if lang_list:
            # Créer une section avec fond gris clair
            lang_data = [[Paragraph("<font color='#ff6b35'><b>LANGUAGES</b></font>", heading_style)]]
            lang_data.append([Paragraph('', normal_style)])  # Ligne de séparation
           
            # Créer des badges pour chaque langue
            badges_text = '  '.join([f"<b>{str(l)}</b>" for l in lang_list if l])
            lang_data.append([Paragraph(badges_text, normal_style)])
           
            lang_section = Table(lang_data, colWidths=[7.2*inch])
            lang_section.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),  # Fond gris clair
                ('TOPPADDING', (0, 0), (-1, -1), 20),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),
                ('RIGHTPADDING', (0, 0), (-1, -1), 20),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (0, 1), (-1, 1), 2, colors.HexColor('#ff6b35')),  # Bordure orange
                ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
            ]))
            story.append(lang_section)
            story.append(Spacer(1, 0.3*inch))
   
    # Certifications avec design inspiré du formulaire
    if cv_data.certifications:
        # S'assurer que certifications est une liste
        if isinstance(cv_data.certifications, str):
            try:
                cert_list = json.loads(cv_data.certifications)
            except:
                cert_list = []
        elif isinstance(cv_data.certifications, list):
            cert_list = cv_data.certifications
        else:
            cert_list = []
       
        if cert_list:
            # Créer une section avec fond gris clair
            cert_data = [[Paragraph("<font color='#ff6b35'><b>CERTIFICATIONS</b></font>", heading_style)]]
            cert_data.append([Paragraph('', normal_style)])  # Ligne de séparation
           
            cert_style = ParagraphStyle(
                'CertStyle',
                parent=normal_style,
                fontSize=11,
                leading=16,
                leftIndent=0,
                rightIndent=0,
                spaceAfter=8
            )
           
            # Ajouter chaque certification
            for cert in cert_list:
                if isinstance(cert, dict):
                    name = cert.get('name', '')
                    issuer = cert.get('issuer', '')
                    date = cert.get('date', '')
                   
                    # Formater la date si elle existe
                    formatted_date = ''
                    if date:
                        try:
                            from datetime import datetime
                            if len(date) == 10:  # Format YYYY-MM-DD
                                date_obj = datetime.strptime(date, '%Y-%m-%d')
                                formatted_date = date_obj.strftime('%B %Y')
                            else:
                                formatted_date = date
                        except:
                            formatted_date = date
                   
                    cert_text = f"<b>{name}</b>"
                    if issuer:
                        cert_text += f"<br/><i>{issuer}</i>"
                    if formatted_date:
                        cert_text += f"<br/>{formatted_date}"
                   
                    cert_data.append([Paragraph(cert_text, cert_style)])
                else:
                    cert_data.append([Paragraph(f"<b>{str(cert)}</b>", cert_style)])
           
            cert_section = Table(cert_data, colWidths=[7.2*inch])
            cert_section.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),  # Fond gris clair
                ('TOPPADDING', (0, 0), (-1, -1), 20),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 20),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),
                ('RIGHTPADDING', (0, 0), (-1, -1), 20),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (0, 1), (-1, 1), 2, colors.HexColor('#ff6b35')),  # Bordure orange
                ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
            ]))
            story.append(cert_section)
            story.append(Spacer(1, 0.3*inch))
   
    # Générer le PDF
    try:
        if not story:
            messages.warning(request, 'Votre CV est vide. Veuillez remplir au moins quelques informations.')
            return redirect('generate_cv')
       
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
       
        # Retourner le PDF
        response = HttpResponse(pdf_data, content_type='application/pdf')
       
        # Créer un nom de fichier sécurisé
        safe_name = (cv_data.full_name or request.user.username or "CV").replace(' ', '_').replace('/', '_').replace('\\', '_')[:50]
        date_str = cv_data.date_updated.strftime('%Y%m%d')
        filename = f"CV_{safe_name}_{date_str}.pdf"
       
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_data)
        return response
       
    except Exception as e:
        import traceback
        error_msg = f'Erreur lors de la génération du PDF: {str(e)}'
        print(f"PDF Generation Error: {error_msg}")
        print(traceback.format_exc())
        messages.error(request, error_msg)
        return redirect('generate_cv')

@csrf_exempt
def toggle_favori(request, offre_id):
    """API pour ajouter/retirer une offre des favoris"""
    from offreStage.models import Favori, OffreStage
    from django.http import JsonResponse
    from django.contrib.auth.decorators import login_required
   
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Vous devez être connecté'}, status=401)
   
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
   
    try:
        offre = OffreStage.objects.get(id_offre=offre_id)
        favori, created = Favori.objects.get_or_create(
            user=request.user,
            offre=offre
        )
       
        if not created:
            # Si le favori existe déjà, le supprimer
            favori.delete()
            return JsonResponse({'success': True, 'is_favori': False, 'message': 'Offre retirée des favoris'})
        else:
            return JsonResponse({'success': True, 'is_favori': True, 'message': 'Offre ajoutée aux favoris'})
   
    except OffreStage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Offre non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def check_favori(request, offre_id):
    """API pour vérifier si une offre est en favoris"""
    from offreStage.models import Favori
    from django.http import JsonResponse
   
    if not request.user.is_authenticated:
        return JsonResponse({'is_favori': False})
   
    is_favori = Favori.objects.filter(user=request.user, offre_id=offre_id).exists()
    return JsonResponse({'is_favori': is_favori})


urlpatterns = [
    # --- ADMIN ---
    path('admin/', admin_dashboard_view, name='admin_dashboard'),
    path('admin/tables/', tables, name='admin_tables'),
    path('admin/edubot/', admin_edubot, name='admin_edubot'),
    path('admin/edubox/', admin_edubox, name='admin_edubox'),
    path('admin/logements/dashboard/', dashboard_logements, name='dashboard_logements'),
    path('admin/logements/', manage_logements, name='manage_logements'),
    path('admin/logements/<int:logement_id>/approve/', approve_logement, name='approve_logement'),
    path('admin/logements/<int:logement_id>/reject/', reject_logement, name='reject_logement'),
    path('admin/<str:page>/', argon_page, name='admin_page'),
    path('dj-admin/', admin.site.urls),

    # --- APPLICATIONS PRINCIPALES ---
    # UserApp.urls doit être avant Startup.urls pour que la route racine pointe vers index.html
    path('', include('UserApp.urls')),
    path('api/', include('UserApp.api_urls')),
    path('Logement/', include('LogementApp.urls')),
    path('Event/', include('EventApp.urls')),  # AJOUT CRITIQUE: URLs pour EventApp
    path('startup/', include('Startup.urls')),  # your app routes
    path('investissements/', include('Investissement.urls')),
    path('startupMembers/', include('StartupMembers.urls')),
    
    # --- DASHBOARD STAGES ---
    path('dashboard/internship/', dashboard, name='dashboard_internships'),
    path('dashboard/offres-stage/', offres_stage, name='offres_stage'),
    path('dashboard/postulations/', postulations, name='postulations'),
    path('dashboard/entretiens/', entretiens, name='entretiens'),
    path('dashboard/calendar/', calendar, name='calendar'),
    # API endpoints pour le calendrier
    path('dashboard/calendar/api/events/', calendar_api_events, name='calendar_api_events'),
    path('dashboard/calendar/api/accepted-applications/', calendar_api_accepted_applications, name='calendar_api_accepted_applications'),
    path('dashboard/calendar/api/events/create/', calendar_api_create_event, name='calendar_api_create_event'),
    path('dashboard/calendar/api/events/<str:event_id>/update-date/', calendar_api_update_event_date, name='calendar_api_update_event_date'),
    path('dashboard/calendar/api/events/<str:event_id>/update/', calendar_api_update_event, name='calendar_api_update_event'),
    path('dashboard/calendar/api/events/<str:event_id>/delete/', calendar_api_delete_event, name='calendar_api_delete_event'),
    path('dashboard/startup/', startup, name='startup'),
    path('dashboard/housing/', housing, name='housing'),
    path('dashboard/ride-sharing/', ride_sharing, name='ride_sharing'),
    path('dashboard/events/', dashboard_events, name='dashboard_events'),
    
    # --- FRONTEND STAGES ---
    path('my-applications/', my_applications, name='my_applications'),
    path('my-interviews/', my_interviews, name='my_interviews'),
    path('my-favoris/', my_favoris, name='my_favoris'),
    path('generate-cv/', generate_cv, name='generate_cv'),
    path('api/favoris/<int:offre_id>/toggle/', toggle_favori, name='toggle_favori'),
    path('api/favoris/<int:offre_id>/check/', check_favori, name='check_favori'),
    path('about/', about, name='about'),
    path('internships/', internships, name='internships'),
    path('postuler/', postuler, name='postuler'),
    path('contact/', contact, name='contact'),
    
    # --- EVENT APP ---
    path('event/<int:event_id>/seats/', views.view_seats, name='view_seats'),
    path('seats/', views.seats_list, name='seats_list'),
    
    # --- ADMIN REDIRIGÉ VERS DASHBOARD ---
    path('edds/', redirect_to_dashboard),

    # --- DASHBOARD COVOITURAGE ---
    path('dashboard/covoiturage/', gl_views.dashboard, name='dashboard_covoiturage'),
    path('reservation_dashboard/', gl_views.reservation_dashboard, name='reservation_dashboard'),
    
    # --- APPROBATION DES OFFRES COVOITURAGE ---
    path('offres/covoiturage/approver/<int:id>/', approver_offre, name='approver_offre'),
    path('offres/covoiturage/rejeter/<int:id>/', rejeter_offre, name='rejeter_offre'),

    # --- PAGE ACCUEIL FRONT COVOITURAGE ---
    path('covoiturage/', include('CovoiturageApp.urls')),
    # --- MODULE COVOITURAGE ---
    path('offres/covoiturage/', covoiturage_views.offre_list, name='offres_list'),
    path('offres/covoiturage/add/', covoiturage_views.offre_create, name='offre_create'),
    path('offres/covoiturage/edit/<int:id>/', covoiturage_views.offre_update, name='offre_update'),
    path('offres/covoiturage/delete/<int:id>/', covoiturage_views.offre_delete, name='offre_delete'),
    path('mes_offres/', covoiturage_views.mes_offres, name='mes_offres'),
    path('covoiturage/', include('CovoiturageApp.urls')),

    # --- MODULE RÉSERVATIONS ---
    path('reservation/', include('ReservationApp.urls')),
    path('dashboard/', views.dashboard, name='dashboard'),

    # --- MODULE STARTUP ---
    

    # Gestion des demandes pour le conducteur
    path('mes_reservations/', mes_reservations, name='mes_reservations'),
    path('reservations/accept/<int:id>/', reservation_accept, name='res_accept'),
    path('reservations/reject/<int:id>/', reservation_reject, name='res_reject'),
    path('mes_reservations_passager/', mes_reservations_passager, name='mes_reservations_passager'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
