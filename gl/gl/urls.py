"""
URL configuration for gl project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import timedelta
# ✅ Ajout pour gérer les fichiers médias (images, CV, etc.)
from django.conf import settings
from django.conf.urls.static import static

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
            offre.delete()
            return redirect('offres_stage')
        else:
            offre_id = request.POST.get('offre_id')
            if offre_id:
                offre = get_object_or_404(OffreStage, id_offre=offre_id)
                form = OffreStageForm(request.POST, request.FILES, instance=offre)
            else:
                form = OffreStageForm(request.POST, request.FILES)
            
            if form.is_valid():
                form.save()
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
        elif 'supprimer' in request.POST:
            postulation_id = request.POST.get('supprimer')
            postulation = get_object_or_404(Postulation, id_postulation=postulation_id)
            postulation.delete()
    
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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/offres-stage/', offres_stage, name='offres_stage'),
    path('dashboard/postulations/', postulations, name='postulations'),
    path('dashboard/entretiens/', entretiens, name='entretiens'),
    path('dashboard/startup/', startup, name='startup'),
    path('dashboard/housing/', housing, name='housing'),
    path('dashboard/ride-sharing/', ride_sharing, name='ride_sharing'),
    path('dashboard/events/', events, name='events'),
    path('my-applications/', my_applications, name='my_applications'),
    path('my-interviews/', my_interviews, name='my_interviews'),
    path('', index, name='index'),
    path('about/', about, name='about'),
    path('internships/', internships, name='internships'),
    path('postuler/', postuler, name='postuler'),
    path('contact/', contact, name='contact'),
]

# ✅ Ces lignes permettent à Django d'afficher les fichiers statiques et médias en mode DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
