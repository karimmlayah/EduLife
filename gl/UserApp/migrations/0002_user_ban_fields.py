from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('UserApp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='ban_reason',
            field=models.TextField(blank=True, null=True, verbose_name='Raison du bannissement'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='banned_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Date de bannissement'),
        ),
    ]

