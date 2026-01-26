from django.contrib import admin
from django.utils.html import format_html
from .models import (
    SiteConfig, ProductCategory, Product, ProductImage,
    DemoRequest, Order, OrderItem, ContactMessage,
    PortfolioMessage, App
)

# SiteConfig Admin
@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'site_email', 'currency', 'currency_symbol', 'is_active', 'updated_at')
    list_editable = ('is_active',)
    readonly_fields = ('updated_at',)
    
    def has_add_permission(self, request):
        # Only allow one site configuration
        return not SiteConfig.objects.exists()

# ProductCategory Admin
@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'display_order', 'is_active', 'product_count', 'created_at')
    list_editable = ('display_order', 'is_active')
    list_filter = ('category_type', 'is_active')
    search_fields = ('name', 'category_type')
    ordering = ('display_order', 'name')

# ProductImage Inline
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ('preview_image',)
    
    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "-"
    preview_image.short_description = 'Preview'

# Product Admin
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'current_price', 'is_featured', 'status', 'display_order', 'created_at')
    list_editable = ('is_featured', 'status', 'display_order')
    list_filter = ('category', 'status', 'is_featured')
    search_fields = ('name', 'description', 'short_description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'published_at', 'formatted_price')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'description', 'short_description')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price', 'formatted_price')
        }),
        ('Images', {
            'fields': ('image', 'thumbnail')
        }),
        ('Display Settings', {
            'fields': ('display_order', 'is_featured', 'status')
        }),
        ('Technical Specifications', {
            'fields': ('specifications',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        })
    )
    inlines = [ProductImageInline]

# DemoRequest Admin
@admin.register(DemoRequest)
class DemoRequestAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'product', 'interest_area', 'status', 'requested_at')
    list_filter = ('status', 'interest_area', 'requested_at')
    search_fields = ('full_name', 'email', 'company', 'message')
    readonly_fields = ('requested_at', 'contacted_at')
    list_editable = ('status',)
    
    def mark_contacted(self, request, queryset):
        queryset.update(status='contacted', contacted_at=timezone.now())
    mark_contacted.short_description = "Mark selected as contacted"
    
    actions = ['mark_contacted']

# OrderItem Inline
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price', 'total_price')
    
    def total_price(self, obj):
        return obj.quantity * obj.price
    total_price.short_description = 'Total'

# Order Admin
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer_name', 'customer_email', 'status', 'total', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('order_number', 'customer_name', 'customer_email', 'customer_phone')
    readonly_fields = ('order_number', 'created_at', 'updated_at', 'formatted_total')
    list_editable = ('status',)
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone', 'customer_address')
        }),
        ('Order Details', {
            'fields': ('order_number', 'subtotal', 'tax', 'total', 'formatted_total')
        }),
        ('Payment & Status', {
            'fields': ('status', 'payment_method', 'payment_status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

# ContactMessage Admin
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('name', 'email', 'message', 'created_at')
    list_editable = ('is_read',)
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected as read"
    
    actions = ['mark_as_read']

# PortfolioMessage Admin
@admin.register(PortfolioMessage)
class PortfolioMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'submitted_at', 'is_read')
    list_filter = ('is_read', 'submitted_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('name', 'email', 'message', 'submitted_at')
    list_editable = ('is_read',)
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected as read"
    
    actions = ['mark_as_read']

# App Admin
@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'preview_image', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'preview_image_field')
    list_filter = ('created_at',)
    
    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "-"
    preview_image.short_description = 'Preview'
    
    def preview_image_field(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="200" />', obj.image.url)
        return "No image uploaded"
    preview_image_field.short_description = 'Image Preview'

# You can also register them without decorators if you prefer:
# admin.site.register(SiteConfig, SiteConfigAdmin)
# admin.site.register(ProductCategory, ProductCategoryAdmin)
# ... etc.

# Note: Make sure to import timezone if using it in actions
# from django.utils import timezone