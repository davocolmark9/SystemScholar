from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Public
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),

    # Auth (Django built-in)
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Applicant Portal
    path('profile/setup/', views.profile_setup, name='profile_setup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('apply/', views.apply_scholarship, name='apply_scholarship'),
    path('application/<uuid:pk>/', views.application_detail, name='application_detail'),
    path('application/<uuid:pk>/submit/', views.submit_application, name='submit_application'),
    path('document/<int:doc_id>/delete/', views.delete_document, name='delete_document'),

    # Coordinator Portal
    path('coordinator/', views.coordinator_dashboard, name='coordinator_dashboard'),
    path('coordinator/application/<uuid:pk>/', views.coordinator_application_detail, name='coordinator_application_detail'),
    path('coordinator/bulk-action/', views.bulk_action, name='bulk_action'),
    path('coordinator/document/<int:doc_id>/verify/', views.verify_document, name='verify_document'),
]
