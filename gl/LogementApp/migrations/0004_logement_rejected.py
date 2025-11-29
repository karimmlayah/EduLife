# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('LogementApp', '0003_logement_model_3d_and_logementimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='logement',
            name='rejected',
            field=models.BooleanField(default=False, verbose_name='Rejeté'),
        ),
    ]

