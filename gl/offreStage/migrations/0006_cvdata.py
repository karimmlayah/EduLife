# Generated manually for CVData model
from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('offreStage', '0005_favori'),
    ]

    operations = [
        migrations.CreateModel(
            name='CVData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(blank=True, max_length=200, null=True, verbose_name='Nom complet')),
                ('phone', models.CharField(blank=True, max_length=20, null=True, verbose_name='Téléphone')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='Email')),
                ('address', models.CharField(blank=True, max_length=255, null=True, verbose_name='Adresse')),
                ('linkedin', models.URLField(blank=True, null=True, verbose_name='LinkedIn')),
                ('github', models.URLField(blank=True, null=True, verbose_name='GitHub')),
                ('website', models.URLField(blank=True, null=True, verbose_name='Site web')),
                ('professional_summary', models.TextField(blank=True, null=True, verbose_name='Résumé professionnel')),
                ('skills', models.JSONField(blank=True, default=list, verbose_name='Compétences')),
                ('education', models.JSONField(blank=True, default=list, verbose_name='Formations')),
                ('experience', models.JSONField(blank=True, default=list, verbose_name='Expériences')),
                ('projects', models.JSONField(blank=True, default=list, verbose_name='Projets')),
                ('languages', models.JSONField(blank=True, default=list, verbose_name='Langues')),
                ('certifications', models.JSONField(blank=True, default=list, verbose_name='Certifications')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date de mise à jour')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cv_data', to=settings.AUTH_USER_MODEL, verbose_name='Utilisateur')),
            ],
            options={
                'verbose_name': 'Données CV',
                'verbose_name_plural': 'Données CV',
                'ordering': ['-date_updated'],
            },
        ),
    ]

