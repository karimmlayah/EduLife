from urllib import request
from .models import Event, Seat
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg
import stripe
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db.models import F

# Décorateur pour vérifier si l'utilisateur est superuser ou admin
def is_superuser_or_admin(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'role') and user.role == 'ADMIN'))

STATIC_USER_ID = "user123"   # id temporaire pour dev (tu peux changer)

def event_home(request):
    STATIC_USER_ID = request.user.id

    events = Event.objects.all()
    user_reserved_seats = Seat.objects.filter(id_user=STATIC_USER_ID)

    # construire le dict attendu par 2.html : {event_id: {"event": Event, "seats": [n1, n2, ...]}}
    my_reservations = {}
    for seat in user_reserved_seats.select_related("event").order_by("event__date", "number"):
        ev = seat.event
        if ev.id not in my_reservations:
            my_reservations[ev.id] = {"event": ev, "seats": []}
        my_reservations[ev.id]["seats"].append(seat.number)

    # prochain événement (optionnel)
    upcoming_event = Event.objects.filter(date__gte=date.today()).order_by('date').first()
    if not upcoming_event and events.exists():
        upcoming_event = events.order_by('-date').first()

    categories = {
        'conference': events.filter(category='conference'),
        'workshop': events.filter(category='workshop'),
        'concert': events.filter(category='concert'),
        'festival': events.filter(category='festival'),
        'autre': events.filter(category='autre'),
    }

    return render(request, 'Fontoffice/2.html', {
        "events": events,
        "categories": categories,
        "upcoming_event": upcoming_event,
        "my_reservations": my_reservations,  # 👈 indispensable
    })
@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def dashboard_events(request):
    """Dashboard avec statistiques des événements"""
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('index')
    
    today = timezone.now().date()
    first_day_of_month = today.replace(day=1)
    
    all_events = Event.objects.all()
    
    # --- EVENT STATS ---
    total_events = all_events.count()
    upcoming_events = all_events.filter(date__gte=today).count()
    past_events = all_events.filter(date__lt=today).count()
    events_this_month = all_events.filter(date__gte=first_day_of_month).count()
    
    # --- SEATS STATS ---
    total_seats = all_events.aggregate(Sum('total_seats'))['total_seats__sum'] or 0
    total_reserved_seats = all_events.aggregate(Sum('reserved_seats'))['reserved_seats__sum'] or 0
    total_available_seats = total_seats - total_reserved_seats
    occupancy_rate = 0
    if total_seats > 0:
        occupancy_rate = (total_reserved_seats / total_seats) * 100
    
    # --- FINANCIAL STATS ---
    total_revenue = 0
    for event in all_events:
        total_revenue += event.reserved_seats * event.price
    avg_price = all_events.aggregate(Avg('price'))['price__avg'] or 0
    
    # --- CATEGORY STATS ---
    events_by_category = all_events.values('category').annotate(count=Count('id')).order_by('-count')
    
    # --- LOCATION STATS ---
    events_by_location = all_events.values('location').annotate(count=Count('id')).order_by('-count')[:5]
    
    # --- RECENT DATA ---
    recent_events = all_events.order_by('-date')[:5]
    
    context = {
        "total_events": total_events,
        "upcoming_events": upcoming_events,
        "past_events": past_events,
        "events_this_month": events_this_month,
        "total_seats": total_seats,
        "total_reserved_seats": total_reserved_seats,
        "total_available_seats": total_available_seats,
        "occupancy_rate": round(occupancy_rate, 2),
        "total_revenue": round(total_revenue, 2),
        "avg_price": round(avg_price, 2),
        "events_by_category": events_by_category,
        "events_by_location": events_by_location,
        "recent_events": recent_events,
    }
    
    return render(request, "Backoffice/pages/dashboard_events.html", context)

@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def dashboard(request):
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('index')
    if request.method == "POST":
        print("POST data:", request.POST)  # Debug
        
        # Action DELETE
        if request.POST.get("action") == "delete":
            event_id = request.POST.get("event_id")
            if event_id:
                Event.objects.filter(id=event_id).delete()
                messages.success(request, "Événement supprimé avec succès")
            return redirect("dashboard")
        
        # Action EDIT
        if request.POST.get("action") == "edit":
            event_id = request.POST.get("event_id")
            if event_id:
                try:
                    event = Event.objects.get(id=event_id)
                    event.name = request.POST.get("name")
                    event.category = request.POST.get("category")
                    event.description = request.POST.get("description")
                    event.price = request.POST.get("price")
                    event.date = request.POST.get("date")
                    event.location = request.POST.get("location")
                    event.total_seats = request.POST.get("total_seats")
                    
                    # Gestion de l'URL photo (accepte data URI sans limite stricte)
                    photo_url = request.POST.get("photo_url", "").strip()
                    event.photo_url = photo_url
                    # Gestion des coordonnées (gérer le cas où 'None' est envoyé comme chaîne)
                    latitude_str = request.POST.get("latitude", "").strip()
                    longitude_str = request.POST.get("longitude", "").strip()
                    event.latitude = float(latitude_str) if latitude_str and latitude_str.lower() != 'none' else None
                    event.longitude = float(longitude_str) if longitude_str and longitude_str.lower() != 'none' else None
                    # Validation personnalisée sans la validation d'URL par défaut
                    if event.photo_url:
                        if (not event.photo_url.startswith('http://') and 
                            not event.photo_url.startswith('https://') and 
                            not event.photo_url.startswith('data:image/')):
                            messages.error(request, "L'URL de l'image doit être une URL valide ou une image encodée en base64.")
                            return redirect("dashboard")
                    
                    # Valider seulement les autres champs
                    event.full_clean(exclude=['photo_url'])
                    event.save()
                    sync_seats(event)

                    messages.success(request, "Événement modifié avec succès")
                    return redirect("dashboard")
                    
                except Event.DoesNotExist:
                    messages.error(request, "Événement non trouvé")
                except ValidationError as e:
                    messages.error(request, f"Erreur de validation: {e}")
            
            return redirect("dashboard")

        # Action CREATE
        name = request.POST.get("name", "").strip()
        category = request.POST.get("category", "").strip()
        description = request.POST.get("description", "").strip()
        price = request.POST.get("price")
        date_val = request.POST.get("date")
        location = request.POST.get("location", "").strip()
        total_seats = request.POST.get("total_seats")
        photo_url = request.POST.get("photo_url", "").strip()
        # Gestion des coordonnées (gérer le cas où 'None' est envoyé comme chaîne)
        latitude_str = request.POST.get("latitude", "").strip()
        longitude_str = request.POST.get("longitude", "").strip()
        latitude = float(latitude_str) if latitude_str and latitude_str.lower() != 'none' else None
        longitude = float(longitude_str) if longitude_str and longitude_str.lower() != 'none' else None

        # Conversion des types
        try:
            price = float(price) if price else 0
            total_seats = int(total_seats) if total_seats else 0
        except (ValueError, TypeError):
            messages.error(request, "Prix ou nombre de places invalide")
            return redirect("dashboard")

        event = Event(
            name=name,
            category=category,
            description=description,
            price=price,
            date=date_val,
            location=location,
            total_seats=total_seats,
            photo_url=photo_url,
            latitude = latitude,
            longitude = longitude,
        )

        try:
            # Validation personnalisée pour photo_url
            if event.photo_url:
                if (not event.photo_url.startswith('http://') and 
                    not event.photo_url.startswith('https://') and 
                    not event.photo_url.startswith('data:image/')):
                    messages.error(request, "L'URL de l'image doit être une URL valide ou une image encodée en base64.")
                    return redirect("dashboard")
            
            # Valider seulement les autres champs
            event.full_clean(exclude=['photo_url'])
            event.save()

            messages.success(request, "Événement créé avec succès")
            return redirect("dashboard")

        except ValidationError as e:
            error_message = "Erreur de validation: "
            for field, errors in e.message_dict.items():
                error_message += f"{field}: {', '.join(errors)} "
            messages.error(request, error_message)

    # Récupérer tous les événements
    events = Event.objects.all().order_by('-date')
    return render(request, "backoffice/pages/dashboard.html", {"events": events})

@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def view_seats(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    seats = event.seats.all().order_by('number')

    reserved_count = seats.filter(status='reserved').count()
    total = event.total_seats
    free_count = total - reserved_count

    percent = int((reserved_count / total) * 100) if total > 0 else 0

    return render(request, 'backoffice/view_seats.html', {
        'event': event,
        'seats': seats,
        'total': total,
        'reserved': reserved_count,
        'free': free_count,
        'percent': percent,
    })
def sync_seats(event):
    seats = event.seats.all()
    current = seats.count()
    total = event.total_seats

    # ✅ Si total_seats a augmenté → créer les nouveaux sièges
    if total > current:
        for num in range(current + 1, total + 1):
            Seat.objects.create(event=event, number=num, status="available")

    # ✅ Si total_seats a diminué → supprimer les sièges non réservés
    elif total < current:
        extra_seats = seats.filter(number__gt=total, status="available")
        extra_seats.delete()

@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def seats_list(request):
    last_id = request.session.get("last_event_seats_id")

    if last_id:
        return redirect("view_seats", event_id=last_id)

    event = Event.objects.order_by("id").first()
    if event:
        return redirect("view_seats", event_id=event.id)


    return redirect("dashboard")

@login_required(login_url='/login/')
def reserve_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    seats = event.seats.all().order_by('number')

    return render(request, 'Fontoffice/reserve_event.html', {
        'event': event,
        'seats': seats,
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,   # ✅ AJOUT OBLIGATOIRE
        'MAPBOX_ACCESS_TOKEN': settings.MAPBOX_ACCESS_TOKEN,  # 👈 obligatoire

    })

stripe.api_key = settings.STRIPE_SECRET_KEY
import json

def create_checkout_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "Bad request"}, status=400)

    data = json.loads(request.body)

    event_id = data.get("event_id")
    seats = data.get("seats", [])
    total_price = data.get("total_price", 0)

    # Sécurité : convertir en float
    try:
        total_price = float(total_price)
    except:
        return JsonResponse({"error": "Invalid price"}, status=400)

    # Convertir en centimes
    amount_cents = int(total_price * 100)

    event = Event.objects.get(id=event_id)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",

        # Stripe collecte lui-même l’email
        customer_creation="always",

        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": event.name},
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }
        ],

        success_url=(
    request.build_absolute_uri('/Event/payment/success/')
    + f"?session_id={{CHECKOUT_SESSION_ID}}&event={event_id}&seats={','.join(seats)}"
),
        cancel_url=request.build_absolute_uri('/Event/?payment=cancel'),
    )

    return JsonResponse({"sessionId": session.id})

def payment_success(request):
    import stripe

    session_id = request.GET.get("session_id")
    event_id = request.GET.get("event")
    seats_raw = request.GET.get("seats")

    # récupérer la session stripe
    checkout_session = stripe.checkout.Session.retrieve(session_id)
    customer_email = checkout_session.customer_details.email


    event = get_object_or_404(Event, id=event_id)
    seat_numbers = seats_raw.split(",")

    STATIC_USER_ID = request.user.id

    # réserver les sièges
    for number in seat_numbers:
        seat = Seat.objects.get(event=event, number=int(number))
        seat.status = Seat.Status.RESERVED
        seat.id_user = STATIC_USER_ID
        seat.save(update_fields=["status", "id_user"])

    # mettre à jour l'évènement
    Event.objects.filter(id=event.id).update(
        reserved_seats=F("reserved_seats") + len(seat_numbers)
    )

    # envoyer email
    from django.core.mail import send_mail
    
    send_mail(
        subject=f"Confirmation – {event.name}",
        message=(
            f"Votre réservation est confirmée.\n\n"
            f"Sièges : {', '.join(seat_numbers)}\n"
            f"Date : {event.date}\nLieu : {event.location}"
        ),
        from_email=None,
        recipient_list=[customer_email],
        fail_silently=False,
    )

    return redirect("/Event/?payment=success")

def payment_cancel(request):
    return redirect("/Event/?payment=cancel")

@csrf_exempt
def liberer_place(request, seat_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Méthode non autorisée")

    seat = get_object_or_404(Seat, id=seat_id)
    event = seat.event

    # Ne décrémente que si le siège était réellement réservé
    if seat.status == Seat.Status.RESERVED:
        seat.status = Seat.Status.AVAILABLE
        seat.id_user = None
        seat.save(update_fields=["status", "id_user"])

        # décrémenter sans passer sous 0
        Event.objects.filter(id=event.id, reserved_seats__gt=0).update(
            reserved_seats=F('reserved_seats') - 1
        )
        # pour renvoyer la valeur actuelle dans la réponse
        event.refresh_from_db(fields=["reserved_seats"])

        return JsonResponse({
            "success": True,
            "message": f"Chaise {seat.number} libérée.",
            "seat_id": str(seat.id),
            "new_status": seat.status,
            "reserved_seats": event.reserved_seats,
        })

    # Si la chaise n'était pas réservée, rien à décrémenter
    return JsonResponse({"success": False, "message": "La chaise n'était pas réservée."})
 