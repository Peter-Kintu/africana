# Generated by Django 5.0.14 on 2025-07-29 22:51

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_student_uuid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
