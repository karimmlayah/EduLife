from django.contrib import admin
from .models import Investissement  # replace with your actual model names

#admin.site.register(Investissement)
from django.contrib import admin
from .models import Investissement

@admin.register(Investissement)
class InvestissementAdmin(admin.ModelAdmin):
    list_display = ("id_invest", "startup", "investor", "montant", "statut", "date")

    actions = ["accept_investments"]

    @admin.action(description="Mark selected investments as ACCEPTED")
    def accept_investments(self, request, queryset):
        for invest in queryset:
            old_status = invest.statut
            invest.statut = "accepted"
            invest.save()    # ⭐ NOW your save() logic runs

        self.message_user(request, "Selected investments marked as accepted.")
