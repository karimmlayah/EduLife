from .models import Event, Seat
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib import messages
from datetime import datetime, date
from django.utils import timezone
import stripe
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db.models import F

STATIC_USER_ID = "user123"   # id temporaire pour dev (tu peux changer)

def event_home(request):
    STATIC_USER_ID = "user123"

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
def dashboard(request):
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
            photo_url=photo_url
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
def seats_list(request):
    last_id = request.session.get("last_event_seats_id")

    if last_id:
        return redirect("view_seats", event_id=last_id)

    event = Event.objects.order_by("id").first()
    if event:
        return redirect("view_seats", event_id=event.id)


    return redirect("dashboard")
def reserve_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    seats = event.seats.all().order_by('number')

    return render(request, 'Fontoffice/reserve_event.html', {
        'event': event,
        'seats': seats,
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,   # ✅ AJOUT OBLIGATOIRE
    })

stripe.api_key = settings.STRIPE_SECRET_KEY
import json

def create_checkout_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body)
    event_id = data.get("event_id")
    selected_seats = data.get("seats")  # liste ["12", "13"]
    total_price = data.get("total_price")

    event = get_object_or_404(Event, id=event_id)

    # ✅ Prix en centimes
    amount_cents = int(float(total_price) * 100)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": f"Billets : {event.name}",
                },
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=f"http://127.0.0.1:8000/Event/payment/success/?event={event.id}&seats={','.join(selected_seats)}",
        cancel_url="http://127.0.0.1:8000/Event/payment/cancel/",
    )

    return JsonResponse({"id": session.id})
def payment_success(request):
    event_id = request.GET.get("event")
    seats_raw = request.GET.get("seats")
    event = get_object_or_404(Event, id=event_id)
    seat_numbers = seats_raw.split(",")

    STATIC_USER_ID = "user123"

    # marquer sièges
    for number in seat_numbers:
        seat = Seat.objects.get(event=event, number=int(number))
        seat.status = Seat.Status.RESERVED
        seat.id_user = STATIC_USER_ID
        seat.save(update_fields=["status", "id_user"])

    # incrément atomique
    Event.objects.filter(id=event.id).update(
        reserved_seats=F('reserved_seats') + len(seat_numbers)
    )
    event.refresh_from_db(fields=["reserved_seats"])

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
 