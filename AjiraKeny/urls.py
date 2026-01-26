
from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('AjiraApp.personal_urls')),
    path('', include('AjiraApp.api_urls')),
    path('', include('AjiraApp.urls')),
]
