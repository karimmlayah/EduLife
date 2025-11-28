# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('LogementApp', '0005_binomerequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='logement',
            name='wifi',
            field=models.BooleanField(default=False, verbose_name='WiFi disponible'),
        ),
        migrations.AddField(
            model_name='logement',
            name='video',
            field=models.URLField(blank=True, help_text='Lien vers une vidéo YouTube, Vimeo, etc.', max_length=500, null=True, verbose_name='Vidéo (URL optionnelle)'),
        ),
        migrations.AddField(
            model_name='logement',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=6, help_text='Coordonnée GPS (sera remplie automatiquement depuis la carte)', max_digits=9, null=True, verbose_name='Latitude'),
        ),
        migrations.AddField(
            model_name='logement',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=6, help_text='Coordonnée GPS (sera remplie automatiquement depuis la carte)', max_digits=9, null=True, verbose_name='Longitude'),
        ),
    ]

