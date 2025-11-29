# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('LogementApp', '0002_logement_approved'),
    ]

    operations = [
        migrations.AddField(
            model_name='logement',
            name='model_3d',
            field=models.URLField(blank=True, help_text='Lien vers un modèle 3D (ex: Sketchfab, etc.)', max_length=500, null=True, verbose_name='Modèle 3D (URL optionnelle)'),
        ),
        migrations.CreateModel(
            name='LogementImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='logements/images/', verbose_name='Image')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('logement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='LogementApp.logement', verbose_name='Logement')),
            ],
            options={
                'verbose_name': 'Image de logement',
                'verbose_name_plural': 'Images de logement',
                'ordering': ['created_at'],
            },
        ),
        migrations.AlterField(
            model_name='logement',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='logements/', verbose_name='Image principale'),
        ),
    ]

