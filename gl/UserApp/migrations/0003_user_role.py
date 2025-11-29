from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('UserApp', '0002_user_ban_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[('UTILISATEUR', 'Utilisateur'), ('ADMIN', 'Administrateur')],
                default='UTILISATEUR',
                max_length=32,
                verbose_name='Rôle',
            ),
        ),
    ]

