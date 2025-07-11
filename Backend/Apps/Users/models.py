from django.db import models

class UserProfile(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    address = models.CharField(max_length=255)
    age = models.PositiveIntegerField()
    # You can add more fields as needed for Airbnb
