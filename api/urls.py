from django.urls import path
from . import views

urlpatterns = [
    # JWT-secured endpoint for external institutions
    path('verify/<uuid:application_id>/', views.verify_applicant_status, name='api_verify_applicant'),
    # Public fallback that returns "Restricted Data"
    path('verify-public/<uuid:application_id>/', views.verify_applicant_status_public, name='api_verify_public'),
]
