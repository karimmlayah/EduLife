# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('LogementApp', '0006_logement_wifi_video_coordinates'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='logement',
            name='video',
        ),
        migrations.AddField(
            model_name='logement',
            name='video',
            field=models.FileField(blank=True, help_text='Fichier vidéo (MP4, WebM, OGG, etc.)', max_length=100, null=True, upload_to='logements/videos/', verbose_name='Vidéo (fichier optionnel)'),
        ),
    ]

