from django.db import models
from django.conf import settings
from Startup.models import Startup   # adjust the import if your app name is different


class StartupMember(models.Model):
    id_member = models.AutoField(primary_key=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="startup_memberships")
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name="members")

    role = models.CharField(max_length=100, default="Member")
    joined_date = models.DateTimeField(auto_now_add=True)

    is_lead = models.BooleanField(default=False)   # founder = True

    class Meta:
        db_table = "startup_member"   # ← custom name
        unique_together = ('user', 'startup')
    def __str__(self):
        return f"{self.user.username} → {self.startup.nom_startup}"
