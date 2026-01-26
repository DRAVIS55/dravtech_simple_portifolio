from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views, tests
urlpatterns = [
path("education/", views.education, name="education"),
    path("skills/", views.skills, name="skills"),
    path("experience/", views.experience, name="experience"),
    path("projects/", views.projects, name="projects"),
    path("references/", views.references, name="references"),
    path("contact/", views.contact, name="contact"),
    path('lives/', views.live, name='lives'),
      path('messages/', views.portfolio_messages, name='portfolio_messages'),
      
 ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)