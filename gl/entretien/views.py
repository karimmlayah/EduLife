from django.shortcuts import render, redirect, get_object_or_404
from .models import Entretien
from .forms import EntretienForm
from postulation.models import Postulation
from django.contrib import messages
from django.db.models import Q

def liste_entretiens(request):
    if request.method == 'POST':
        if 'supprimer_entretien' in request.POST:
            entretien_id = request.POST.get('supprimer_entretien')
            entretien = get_object_or_404(Entretien, id_entretien=entretien_id)
            entretien.delete()
            messages.success(request, 'Entretien supprimé avec succès.')
            return redirect('entretiens')
        elif 'supprimer_postulation' in request.POST:
            postulation_id = request.POST.get('supprimer_postulation')
            postulation = get_object_or_404(Postulation, id_postulation=postulation_id)
            postulation.delete()
            messages.success(request, 'Postulation supprimée avec succès.')
            return redirect('entretiens')
        elif 'ajouter' in request.POST:
            from django.utils.dateparse import parse_datetime
            postulation_id = request.POST.get('ajouter')
            postulation = get_object_or_404(Postulation, id_postulation=postulation_id, statut='acceptee')
            date_entretien_str = request.POST.get('date_entretien')
            lien_meet = request.POST.get('lien_meet', '')
            commentaire = request.POST.get('commentaire', '')
            statut = request.POST.get('statut', 'planifie')
            
            # Convertir la date string en datetime
            date_entretien = parse_datetime(date_entretien_str.replace('T', ' '))
            if not date_entretien:
                from datetime import datetime
                date_entretien = datetime.strptime(date_entretien_str, '%Y-%m-%dT%H:%M')
            
            entretien = Entretien.objects.create(
                postulation=postulation,
                date_entretien=date_entretien,
                lien_meet=lien_meet if lien_meet else None,
                commentaire=commentaire if commentaire else None,
                statut=statut
            )
            messages.success(request, 'Entretien ajouté avec succès.')
            return redirect('entretiens')
        elif 'modifier' in request.POST:
            entretien_id = request.POST.get('modifier')
            entretien = get_object_or_404(Entretien, id_entretien=entretien_id)
            form = EntretienForm(request.POST, instance=entretien)
            if form.is_valid():
                form.save()
                messages.success(request, 'Entretien modifié avec succès.')
                return redirect('entretiens')
    
    # Postulations acceptées sans entretien
    postulations_acceptees = Postulation.objects.filter(
        statut='acceptee'
    ).exclude(
        entretien__isnull=False
    ).select_related('offre')
    
    # Recherche
    search_query = request.GET.get('search', '')
    if search_query:
        postulations_acceptees = postulations_acceptees.filter(
            Q(email__icontains=search_query) |
            Q(offre__titre__icontains=search_query)
        )
    
    # Tri
    sort_by = request.GET.get('sort', '-date_postulation')
    if sort_by == 'date':
        postulations_acceptees = postulations_acceptees.order_by('date_postulation')
    elif sort_by == '-date':
        postulations_acceptees = postulations_acceptees.order_by('-date_postulation')
    elif sort_by == 'email':
        postulations_acceptees = postulations_acceptees.order_by('email')
    elif sort_by == '-email':
        postulations_acceptees = postulations_acceptees.order_by('-email')
    elif sort_by == 'offre':
        postulations_acceptees = postulations_acceptees.order_by('offre__titre')
    elif sort_by == '-offre':
        postulations_acceptees = postulations_acceptees.order_by('-offre__titre')
    else:
        postulations_acceptees = postulations_acceptees.order_by('-date_postulation')
    
    form = EntretienForm()
    
    context = {
        'postulations_acceptees': postulations_acceptees,
        'form': form,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'stages/Backoffice/entretiens.html', context)
