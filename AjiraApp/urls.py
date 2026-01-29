# urls.py - Complete URL configuration
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views, tests

urlpatterns = [
    path('video/', views.videos, name='videos'),
    path('about/', views.index, name='about'),
    # =============================================================================
    # Main Admin Dashboard
    # =============================================================================
    path('dravtech/admin/login/', views.dravtech_admin_login, name='dravtech_admin_login'),
    path('dravtech/admin/dashboard/', views.admin_dashboard, name='dravtech_admin_dashboard'),
    
    # =============================================================================
    # Marketplace Public Routes
    # =============================================================================
    path('', views.marketplace_home, name='marketplace_home'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    
    # =============================================================================
    # Test Routes
    # =============================================================================
    path("prof-mutimbei/", tests.prof_mutembei, name="prof_mutembei"),
    path("omanyala/", tests.omanyala_portfolio, name="omanyala_portfolio"),
    
    # =============================================================================
    # Portfolio Routes
    # =============================================================================
    path("download/", views.download_app, name="download_app"),
    path("portifolio/", views.portifolio, name="portifolio"),
    path("software-engineer/samuel/", views.home, name="home"),
    path("about-us/", views.about_us, name="about_us"),
    path("personal-profile/", views.personal_profile, name="personal_profile"),
    
    
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
from django.views.generic import TemplateView

urlpatterns += [
    path("sitemap.xml", TemplateView.as_view(
        template_name="sitemap.xml",
        content_type="application/xml"
    ), name="sitemap"),
]
urlpatterns += [
    path("robots.txt", TemplateView.as_view(
        template_name="robots.txt",
        content_type="text/plain"
    ), name="robots"),
]

# =============================================================================
# Custom Error Handlers
# =============================================================================
handler404 = 'AjiraApp.views.page_not_found'
handler500 = 'AjiraApp.views.server_error'
handler403 = 'AjiraApp.views.permission_denied'
handler400 = 'AjiraApp.views.bad_request'

