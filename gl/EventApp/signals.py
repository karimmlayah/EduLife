from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Event, Seat

@receiver(post_save, sender=Event)
def create_event_seats(sender, instance, created, **kwargs):
    if created and instance.total_seats:
        seats = [
            Seat(event=instance, number=i)
            for i in range(1, instance.total_seats + 1)
        ]
        Seat.objects.bulk_create(seats)
