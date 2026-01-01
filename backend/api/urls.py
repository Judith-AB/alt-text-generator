from django.urls import path
from .views import generate_alt_text

urlpatterns = [
    path('generate-alt-text/', generate_alt_text),
]
