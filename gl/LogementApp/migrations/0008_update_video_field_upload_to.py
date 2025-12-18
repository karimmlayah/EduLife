# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('LogementApp', '0007_change_video_to_filefield'),
    ]

    operations = [
        migrations.AlterField(
            model_name='logement',
            name='video',
            field=models.FileField(
                blank=True,
                help_text='Fichier vidéo (MP4, WebM, OGG, etc.)',
                max_length=100,
                null=True,
                upload_to='logements/videos/',
                verbose_name='Vidéo (fichier optionnel)'
            ),
        ),
    ]

