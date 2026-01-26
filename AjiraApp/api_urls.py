from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views, tests
urlpatterns = [
# =============================================================================
    # Public API Endpoints
    # =============================================================================
    path('api/products/', views.api_products, name='api_products'),
    path('api/categories/', views.api_categories, name='api_categories'),
    path('api/demo-request/', views.api_demo_request, name='api_demo_request'),
    path('api/order/', views.api_order, name='api_order'),
    path('api/product/<int:product_id>/', views.api_product_detail, name='api_product_detail'),
    path('api/category/<int:category_id>/', views.api_category_detail, name='api_category_detail'),
    path('api/demo/<int:demo_id>/', views.api_demo_detail, name='api_demo_detail'),
    path('api/currency/', views.get_currency_symbol, name='get_currency_symbol'),
    path('api/apps/', views.apps_api, name='apps_api'),
    path('api/contact/', views.api_contact, name='api_contact'),
    
    # =============================================================================
    # Admin API Endpoints (AJAX)
    # =============================================================================
    
    # Dashboard Statistics
    path('dravtech/admin/api/stats/', views.get_dashboard_stats, name='get_dashboard_stats'),
    path('dravtech/admin/api/refresh/', views.refresh_dashboard, name='refresh_dashboard'),
    
    # Products Management
    path('dravtech/admin/api/products/', views.get_all_products, name='get_all_products'),
    path('dravtech/admin/api/products/create/', views.create_product, name='api_create_product'),
    path('dravtech/admin/api/products/<int:product_id>/', views.get_product, name='api_get_product'),
    path('dravtech/admin/api/products/<int:product_id>/edit/', views.edit_product, name='api_edit_product'),
    path('dravtech/admin/api/products/<int:product_id>/delete/', views.delete_product, name='api_delete_product'),
    
    # Categories Management
    path('dravtech/admin/api/categories/', views.get_all_categories, name='get_all_categories'),
    path('dravtech/admin/api/categories/create/', views.create_category, name='api_create_category'),
    path('dravtech/admin/api/categories/<int:category_id>/', views.get_category, name='api_get_category'),
    path('dravtech/admin/api/categories/<int:category_id>/edit/', views.edit_category, name='api_edit_category'),
    path('dravtech/admin/api/categories/<int:category_id>/delete/', views.delete_category, name='api_delete_category'),
    
    # Site Configuration
    path('dravtech/admin/api/config/', views.get_site_config, name='api_get_site_config'),
    path('dravtech/admin/api/config/update/', views.update_site_config, name='api_update_site_config'),
    
    # Demo Requests Management
    path('dravtech/admin/api/demos/', views.get_all_demos, name='get_all_demos'),
    path('dravtech/admin/api/demos/<int:demo_id>/', views.get_demo_details, name='api_get_demo_details'),
    path('dravtech/admin/api/demos/<int:demo_id>/status/', views.update_demo_status, name='api_update_demo_status'),
    path('dravtech/admin/api/demos/<int:demo_id>/delete/', views.delete_demo, name='api_delete_demo'),
    
    # Orders Management
    path('dravtech/admin/api/orders/', views.get_all_orders, name='get_all_orders'),
    path('dravtech/admin/api/orders/<int:order_id>/', views.get_order_details, name='api_get_order_details'),
    path('dravtech/admin/api/orders/<int:order_id>/status/', views.update_order_status, name='api_update_order_status'),
    
    # Messages Management
    path('dravtech/admin/api/messages/', views.get_all_messages, name='get_all_messages'),
    path('dravtech/admin/api/messages/<str:message_type>/<int:message_id>/', 
         views.get_message_details, name='api_get_message_details'),
    path('dravtech/admin/api/messages/<str:message_type>/<int:message_id>/read/', 
         views.mark_message_read, name='api_mark_message_read'),
    path('dravtech/admin/api/messages/<str:message_type>/<int:message_id>/delete/', 
         views.delete_message, name='api_delete_message'),
    path('dravtech/admin/api/messages/clear/', views.clear_all_messages, name='api_clear_all_messages'),
    
    # =============================================================================
    # Legacy Admin Routes (For compatibility - redirect to AJAX system)
    # =============================================================================
    
    # Products Management (Legacy)
    path('dravtech/admin/product/create/', views.create_product, name='create_product'),
    path('dravtech/admin/product/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('dravtech/admin/product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    
    # Categories Management (Legacy)
    path('dravtech/admin/category/create/', views.create_category, name='create_category'),
    path('dravtech/admin/category/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('dravtech/admin/category/<int:category_id>/delete/', views.delete_category, name='delete_category'),
    
    # Messages Management (Legacy)
    path('dravtech/admin/messages/', views.admin_messages, name='admin_messages'),
    path('dravtech/admin/messages/clear/', views.clear_messages, name='clear_messages'),
    path('dravtech/admin/messages/<str:message_type>/<int:message_id>/', 
         views.message_detail, name='message_detail'),
    path('dravtech/admin/messages/<str:message_type>/<int:message_id>/delete/', 
         views.delete_message, name='delete_message'),
    
    # Demo Requests Management (Legacy)
    path('dravtech/admin/demo-requests/', views.demo_requests, name='demo_requests'),
    path('dravtech/admin/demo/<int:demo_id>/status/', views.update_demo_status, name='update_demo_status'),
    
    # Orders Management (Legacy)
    path('dravtech/admin/orders/', views.admin_orders, name='admin_orders'),
    path('dravtech/admin/order/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    
    # Site Configuration (Legacy)
    path('dravtech/admin/site-config/', views.site_config, name='site_config'),
    
    # =============================================================================
    # Django Admin (Original - Keep separate from custom admin)
    # =============================================================================
    path('admin/', admin.site.urls),
    
    # =============================================================================
    # Error Handlers
    # =============================================================================
    path('404/', views.page_not_found, name='page_not_found'),
    path('500/', views.server_error, name='server_error'),
    path('api/apps/', views.apps_api, name='apps_api'),  # GET all, POST create
    path('api/apps/<int:app_id>/', views.apps_api, name='apps_api_detail'),  # GET single, PUT update, DELETE
    
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
