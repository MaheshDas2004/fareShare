from django.contrib import admin

# Apne model ko import karein
from .models import User

# Model ko register karein
admin.site.register(User)