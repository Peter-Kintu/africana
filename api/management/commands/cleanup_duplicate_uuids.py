import os
from django.core.management.base import BaseCommand
from django.db.models import Count
from api.models import Student
import uuid

class Command(BaseCommand):
    help = 'Fix duplicate UUIDs in Student model'

    def handle(self, *args, **kwargs):
        duplicates = Student.objects.values('uuid').annotate(count=Count('uuid')).filter(count__gt=1)
        fixed = 0

        for entry in duplicates:
            students = Student.objects.filter(uuid=entry['uuid'])
            for student in students[1:]:  # keep one, fix others
                student.uuid = uuid.uuid4()
                student.save()
                fixed += 1

        self.stdout.write(self.style.SUCCESS(f'Done! Fixed {fixed} duplicate UUID(s).'))

os.makedirs('api/management/commands', exist_ok=True)
open('api/management/__init__.py', 'a').close()
open('api/management/commands/__init__.py', 'a').close()