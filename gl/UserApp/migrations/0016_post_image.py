# Generated manually for adding image field to Post model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('UserApp', '0015_adminmessage_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='posts/images/', verbose_name='Image'),
        ),
    ]





