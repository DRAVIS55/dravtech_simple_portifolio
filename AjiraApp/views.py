# views.py - Complete Updated Views
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages as django_messages
from django.db.models import Count, Q, Sum, F, Value
from django.db.models.functions import Concat
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
import json
import uuid
from datetime import datetime, timedelta
import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .models import (
    Product, ProductCategory, DemoRequest, Order, OrderItem,
    ContactMessage, PortfolioMessage, ProductImage, SiteConfig
)
from .forms import ProductForm, CategoryForm, SiteConfigForm

# ============================================================================
# Helper Functions
# ============================================================================

def page_not_found(request, exception):
    return render(request, '404.html', status=404)

def server_error(request):
    return render(request, '500.html', status=500)

def permission_denied(request, exception):
    return render(request, '403.html', status=403)

def bad_request(request, exception):
    return render(request, '400.html', status=400)

def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and user.is_staff




def dravtech_admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember = request.POST.get("remember")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # OPTIONAL: restrict ONLY staff/admin users
            if not user.is_staff:
                messages.error(request, "You do not have admin access.")
                return redirect("dravtech_admin_login")

            login(request, user)

            # Remember me OFF → expire session when browser closes
            if not remember:
                request.session.set_expiry(0)  

            return redirect("dravtech_admin_dashboard")

        else:
            messages.error(request, "Invalid username or password.")
            return redirect("dravtech_admin_login")

    return render(request, "login.html")


# ============================================================================
# Public Views (Marketplace)
# ============================================================================


def marketplace_home(request):
    """Main marketplace page"""
    # Get featured products for initial load
    featured_products = Product.objects.filter(
        status='published', 
        is_featured=True
    ).select_related('category').order_by('display_order')[:8]
    
    # Get categories for navigation
    categories = ProductCategory.objects.filter(is_active=True).order_by('display_order')
    
    # Get site config for currency
    site_config = SiteConfig.objects.filter(is_active=True).first()
    if not site_config:
        site_config = SiteConfig.objects.create()
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'site_config': site_config,
    }
    return render(request, 'marketplace/index.html', context)

def product_detail(request, slug):
    """Product detail page"""
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images'),
        slug=slug, 
        status='published'
    )
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        status='published'
    ).exclude(id=product.id).order_by('display_order')[:4]
    
    # Get site config
    site_config = SiteConfig.objects.filter(is_active=True).first()
    
    context = {
        'product': product,
        'related_products': related_products,
        'site_config': site_config,
    }
    return render(request, 'marketplace/product_detail.html', context)

# ============================================================================
# Admin Dashboard Views (Main Entry Point)
# ============================================================================

@login_required(login_url='dravtech_admin_login')
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Main admin dashboard with all data loaded dynamically"""
    # Get all data for initial page load
    products = Product.objects.all().select_related('category').order_by('-created_at')[:10]
    categories = ProductCategory.objects.all()
    demo_requests = DemoRequest.objects.all().order_by('-requested_at')[:5]
    orders = Order.objects.all().order_by('-created_at')[:5]
    contact_messages = ContactMessage.objects.filter(is_read=False).order_by('-created_at')[:10]
    portfolio_messages = PortfolioMessage.objects.filter(is_read=False).order_by('-submitted_at')[:10]
    
    # Get or create SiteConfig
    site_config = SiteConfig.objects.filter(is_active=True).first()
    if not site_config:
        site_config = SiteConfig.objects.create()
    
    # Statistics
    stats = {
        'total_products': Product.objects.count(),
        'published_products': Product.objects.filter(status='published').count(),
        'draft_products': Product.objects.filter(status='draft').count(),
        'archived_products': Product.objects.filter(status='archived').count(),
        'categories_count': ProductCategory.objects.count(),
        'active_categories': ProductCategory.objects.filter(is_active=True).count(),
        'demo_requests_count': DemoRequest.objects.count(),
        'pending_demos': DemoRequest.objects.filter(status='pending').count(),
        'total_orders': Order.objects.count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'completed_orders': Order.objects.filter(status='completed').count(),
        'revenue_total': str(Order.objects.filter(status='completed').aggregate(
            total=Sum('total')
        )['total'] or 0),
        'unread_contacts': ContactMessage.objects.filter(is_read=False).count(),
        'unread_portfolio': PortfolioMessage.objects.filter(is_read=False).count(),
        'total_messages': ContactMessage.objects.count() + PortfolioMessage.objects.count(),
    }
    
    # Get unique category types for suggestions
    existing_types = ProductCategory.objects.values_list('category_type', flat=True).distinct()
    
    # Recent activity (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_activity = []
    
    # Recent products
    recent_products = Product.objects.filter(created_at__gte=week_ago)[:3]
    for product in recent_products:
        recent_activity.append({
            'type': 'product',
            'action': 'created' if product.status == 'draft' else 'published',
            'item': product.name,
            'time': product.created_at,
            'user': 'Admin'
        })
    
    # Recent orders
    recent_orders = Order.objects.filter(created_at__gte=week_ago)[:3]
    for order in recent_orders:
        recent_activity.append({
            'type': 'order',
            'action': 'placed',
            'item': f"Order #{order.order_number}",
            'time': order.created_at,
            'user': order.customer_name
        })
    
    # Recent demo requests
    recent_demos = DemoRequest.objects.filter(requested_at__gte=week_ago)[:3]
    for demo in recent_demos:
        recent_activity.append({
            'type': 'demo',
            'action': 'requested',
            'item': f"Demo from {demo.full_name}",
            'time': demo.requested_at,
            'user': demo.full_name
        })
    
    # Sort by time
    recent_activity.sort(key=lambda x: x['time'], reverse=True)
    
    context = {
        'products': products,
        'categories': categories,
        'demo_requests': demo_requests,
        'orders': orders,
        'contact_messages': contact_messages,
        'portfolio_messages': portfolio_messages,
        'site_config': site_config,
        'stats': stats,
        'existing_types': existing_types,
        'recent_activity': recent_activity[:10],  # Limit to 10
    }
    return render(request, 'admin/dashboard.html', context)

# ============================================================================
# API Views for AJAX (Public API)
# ============================================================================
# views.py - Add this to your views


@require_http_methods(["GET"])
def api_products(request):
    """Optimized API endpoint for fetching products with caching"""
    cache_key = 'api_products_all'
    category_type = request.GET.get('category_type', '')
    featured = request.GET.get('featured', '')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 12))
    
    # Try to get from cache first
    if not category_type and not featured:
        cached_data = cache.get(f'{cache_key}_page{page}')
        if cached_data:
            return JsonResponse(cached_data, safe=False)
    
    # Build optimized query
    products = Product.objects.filter(status='published').select_related('category')
    
    if category_type:
        products = products.filter(category__category_type=category_type)
    
    if featured == 'true':
        products = products.filter(is_featured=True)
    
    # Order and paginate
    products = products.order_by('display_order', '-created_at')
    paginator = Paginator(products, per_page)
    
    try:
        page_obj = paginator.page(page)
    except:
        return JsonResponse({'error': 'Invalid page'}, status=400)
    
    # Optimized serialization
    product_list = []
    for product in page_obj:
        product_data = {
            'id': product.id,
            'name': product.name,
            'slug': product.slug,
            'category': product.category.name,
            'category_type': product.category.category_type,
            'short_description': product.short_description,
            'price': str(product.price),
            'discount_price': str(product.discount_price) if product.discount_price else None,
            'current_price': str(product.current_price),
            'has_discount': product.has_discount,
            'image_url': product.image.url if product.image else '',
            'thumbnail_url': product.thumbnail.url if product.thumbnail else product.image.url if product.image else '',
            'specifications': product.specifications,
            'is_featured': product.is_featured,
            'created_at': product.created_at.strftime('%Y-%m-%d %H:%M'),
        }
        product_list.append(product_data)
    
    response_data = {
        'products': product_list,
        'total': paginator.count,
        'page': page,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    }
    
    # Cache the response for 5 minutes if it's a general query
    if not category_type and not featured:
        cache.set(f'{cache_key}_page{page}', response_data, 300)
    
    return JsonResponse(response_data, safe=False)

@require_http_methods(["GET"])
def api_categories(request):
    """API endpoint for categories with caching"""
    cache_key = 'api_categories_all'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data, safe=False)
    
    categories = ProductCategory.objects.filter(is_active=True).order_by('display_order')
    
    category_list = []
    for category in categories:
        category_data = {
            'id': category.id,
            'name': category.name,
            'category_type': category.category_type,
            'type_display': category.category_type,
            'product_count': category.products.filter(status='published').count(),
        }
        category_list.append(category_data)
    
    response_data = {'categories': category_list}
    cache.set(cache_key, response_data, 600)  # Cache for 10 minutes
    
    return JsonResponse(response_data, safe=False)
from .models import ContactMessage
from django.utils import timezone
@csrf_exempt
@require_http_methods(["POST"])
def api_contact(request):
    try:
        data = json.loads(request.body)

        # Validate required fields
        required_fields = ['name', 'email', 'message']
        for field in required_fields:
            if field not in data or not data[field].strip():
                return JsonResponse({
                    'success': False,
                    'error': f'{field.replace("_", " ").title()} is required'
                }, status=400)

        # Build message content
        message_content = f"""
Name: {data['name'].strip()}
Email: {data['email'].strip()}
Phone: {data.get('phone', 'Not provided').strip()}
Service: {data.get('service', 'Not specified').strip()}

Message:
{data['message'].strip()}

Submitted At: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # Save message
        contact_message = ContactMessage.objects.create(
            name=data['name'].strip(),
            email=data['email'].strip(),
            message=message_content
        )

        # USER EMAIL — plain text only
        user_message = f"""
Hello {data['name'].strip()},

We have received your message at DravTech.

Details:
{message_content}

We will reply within 24–48 hours.
Thank you.
"""

        try:
            send_mail(
                subject="DravTech - Message Received",
                message=user_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[data['email'].strip()],
                fail_silently=False,
            )
        except Exception as e:
            print(f"User email failed: {e}")

        # ADMIN EMAIL — plain text
        admin_message = f"""
New contact message received:

{message_content}

Message ID: {contact_message.id}
"""

        try:
            send_mail(
                subject=f"New Contact Message from {data['name'].strip()}",
                message=admin_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Admin email failed: {e}")

        return JsonResponse({
            'success': True,
            'message': 'Message sent successfully!',
            'contact_id': contact_message.id,
            'submitted_at': contact_message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@csrf_exempt
@require_http_methods(["POST"])
def api_demo_request(request):
    try:
        data = json.loads(request.body)

        # Validate required fields
        required_fields = ['full_name', 'email']
        for field in required_fields:
            if field not in data or not data[field].strip():
                return JsonResponse({'error': f'{field} is required'}, status=400)

        # Create the request
        demo_request = DemoRequest.objects.create(
            full_name=data['full_name'].strip(),
            email=data['email'].strip(),
            phone=data.get('phone', '').strip(),
            company=data.get('company', '').strip(),
            message=data.get('message', '').strip(),
            interest_area=data.get('interest_area', '').strip(),
        )

        # Link product if provided
        try:
            product_id = data.get('product_id')
            if product_id:
                product = Product.objects.get(id=product_id, status='published')
                demo_request.product = product
                demo_request.save()
        except Product.DoesNotExist:
            pass

        # EMAIL TO USER — plain text
        user_message = f"""
Hello {demo_request.full_name},

Thank you for requesting a demo at DravTech.

Details:
Name: {demo_request.full_name}
Email: {demo_request.email}
Phone: {demo_request.phone}
Company: {demo_request.company}
Interest Area: {demo_request.interest_area}
Message: {demo_request.message}
Product: {demo_request.product.name if demo_request.product else 'General Inquiry'}

We will follow up soon.
"""

        try:
            send_mail(
                subject="DravTech - Demo Request Confirmation",
                message=user_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[demo_request.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"User email failed: {e}")

        # ADMIN EMAIL
        admin_message = f"""
New demo request received:

Name: {demo_request.full_name}
Email: {demo_request.email}
Phone: {demo_request.phone}
Company: {demo_request.company}
Interest Area: {demo_request.interest_area}
Message: {demo_request.message}
Product: {demo_request.product.name if demo_request.product else 'General Inquiry'}
Requested At: {demo_request.requested_at}

Follow up within 24 hours.
"""

        try:
            send_mail(
                subject=f"New Demo Request: {demo_request.full_name}",
                message=admin_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Admin email failed: {e}")

        return JsonResponse({
            'success': True,
            'message': 'Demo request submitted successfully.',
            'request_id': demo_request.id
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@csrf_exempt
@require_http_methods(["POST"])
def api_order(request):
    try:
        data = json.loads(request.body)

        # Validate required fields
        required_fields = [
            'customer_name', 'customer_email', 'customer_phone',
            'customer_address', 'products', 'total'
        ]
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'{field} is required'}, status=400)

        # Create order
        order = Order.objects.create(
            customer_name=data['customer_name'].strip(),
            customer_email=data['customer_email'].strip(),
            customer_phone=data['customer_phone'].strip(),
            customer_address=data['customer_address'].strip(),
            subtotal=data.get('subtotal', data['total']),
            tax=data.get('tax', 0),
            total=data['total'],
            payment_method=data.get('payment_method', '')
        )

        # Add products
        for item in data['products']:
            try:
                product = Product.objects.get(id=item['product_id'], status='published')
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.get('quantity', 1),
                    price=item.get('price', product.current_price)
                )
            except Product.DoesNotExist:
                pass

        # EMAIL TO USER — plain text
        order_message = f"""
Hello {order.customer_name},

Thank you for your order!

Order Number: {order.order_number}
Total: {order.total}

We will contact you shortly.

Regards,
DravTech Marketplace
"""

        try:
            send_mail(
                subject=f"Order Confirmation #{order.order_number}",
                message=order_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.customer_email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Order confirmation email failed: {e}")

        return JsonResponse({
            'success': True,
            'order_number': order.order_number,
            'message': 'Order placed successfully.'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# views.py
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Product, ProductCategory, App, DemoRequest, Order, ContactMessage, PortfolioMessage, SiteConfig
import json

# Apps API
@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def apps_api(request, app_id=None):
    # ------------------- GET ALL APPS or SINGLE APP -------------------
    if request.method == "GET":
        if app_id:
            # Get single app
            try:
                app = App.objects.get(id=app_id)
                return JsonResponse({
                    "success": True,
                    "app": app.to_dict()
                }, status=200)
            except App.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "App not found"
                }, status=404)
            except Exception as e:
                return JsonResponse({
                    "success": False,
                    "error": str(e)
                }, status=500)
        else:
            # Get all apps
            try:
                apps = App.objects.all().order_by("-created_at")
                
                # Optional filtering
                search = request.GET.get('search', '')
                if search:
                    apps = apps.filter(name__icontains=search)
                
                return JsonResponse({
                    "success": True,
                    "count": apps.count(),
                    "apps": [app.to_dict() for app in apps]
                }, status=200)
            except Exception as e:
                return JsonResponse({
                    "success": False,
                    "error": str(e)
                }, status=500)

    # ------------------- CREATE APP -------------------
    elif request.method == "POST":
        try:
            # Check if it's JSON or form-data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                name = data.get("name")
                url = data.get("url")
                description = data.get("description")
                # Image cannot be sent via JSON, use separate endpoint for image upload
            else:
                # Form-data (multipart)
                name = request.POST.get("name")
                url = request.POST.get("url")
                description = request.POST.get("description")
                image = request.FILES.get("image")

            # Validate required fields
            if not name or not url or not description:
                return JsonResponse({
                    "success": False,
                    "error": "name, url and description are required fields"
                }, status=400)

            # Create app
            app_data = {
                "name": name,
                "url": url,
                "description": description,
            }
            
            # Add image if provided (form-data only)
            if 'image' in locals() and image:
                app_data["image"] = image
            
            app = App.objects.create(**app_data)

            return JsonResponse({
                "success": True,
                "message": "App created successfully",
                "app": app.to_dict()
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({
                "success": False,
                "error": "Invalid JSON format"
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)

    # ------------------- UPDATE APP -------------------
    elif request.method == "PUT":
        if not app_id:
            return JsonResponse({
                "success": False,
                "error": "App ID is required for update"
            }, status=400)
        
        try:
            app = App.objects.get(id=app_id)
            
            # Parse request data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            
            # Update fields
            if 'name' in data:
                app.name = data['name']
            if 'url' in data:
                app.url = data['url']
            if 'description' in data:
                app.description = data['description']
            
            # Handle image update (form-data only)
            if request.FILES.get('image'):
                app.image = request.FILES['image']
            
            app.save()
            
            return JsonResponse({
                "success": True,
                "message": "App updated successfully",
                "app": app.to_dict()
            }, status=200)
            
        except App.DoesNotExist:
            return JsonResponse({
                "success": False,
                "error": "App not found"
            }, status=404)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)

    # ------------------- DELETE APP -------------------
    elif request.method == "DELETE":
        if not app_id:
            return JsonResponse({
                "success": False,
                "error": "App ID is required for deletion"
            }, status=400)
        
        try:
            app = App.objects.get(id=app_id)
            app.delete()
            
            return JsonResponse({
                "success": True,
                "message": "App deleted successfully"
            }, status=200)
            
        except App.DoesNotExist:
            return JsonResponse({
                "success": False,
                "error": "App not found"
            }, status=404)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)

# Admin Dashboard Stats
@require_http_methods(["GET"])
def admin_stats(request):
    try:
        total_products = Product.objects.count()
        published_products = Product.objects.filter(status='published').count()
        categories_count = ProductCategory.objects.filter(is_active=True).count()
        category_types = ProductCategory.objects.values_list('category_type', flat=True).distinct().count()
        total_apps = App.objects.count()
        demo_requests_count = DemoRequest.objects.count()
        pending_demos = DemoRequest.objects.filter(status='pending').count()
        total_orders = Order.objects.count()
        revenue_total = Order.objects.filter(status='completed').aggregate(Sum('total'))['total__sum'] or 0
        
        # Count unread messages
        unread_messages = ContactMessage.objects.filter(is_read=False).count()
        unread_messages += PortfolioMessage.objects.filter(is_read=False).count()
        
        return JsonResponse({
            "success": True,
            "stats": {
                "total_products": total_products,
                "published_products": published_products,
                "categories_count": categories_count,
                "category_types": category_types,
                "total_apps": total_apps,
                "demo_requests_count": demo_requests_count,
                "pending_demos": pending_demos,
                "total_orders": total_orders,
                "revenue_total": revenue_total,
                "unread_messages": unread_messages
            }
        }, status=200)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

# Admin Refresh Data
@require_http_methods(["GET"])
def admin_refresh(request):
    try:
        # Get recent products
        recent_products = Product.objects.all().order_by('-created_at')[:5]
        products_data = [{
            'name': p.name,
            'category': p.category.name if p.category else 'Uncategorized',
            'status': p.status
        } for p in recent_products]
        
        # Get recent apps
        recent_apps = App.objects.all().order_by('-created_at')[:5]
        apps_data = [{
            'name': a.name,
            'url': a.url
        } for a in recent_apps]
        
        # Get recent demos
        recent_demos = DemoRequest.objects.all().order_by('-requested_at')[:5]
        demos_data = [{
            'name': d.full_name,
            'product': d.product.name if d.product else 'General Inquiry',
            'status': d.status
        } for d in recent_demos]
        
        # Get recent orders
        recent_orders = Order.objects.all().order_by('-created_at')[:5]
        orders_data = [{
            'order_number': o.order_number,
            'customer': o.customer_name,
            'total': o.total,
            'status': o.status
        } for o in recent_orders]
        
        # Get recent messages
        recent_contact_msgs = ContactMessage.objects.all().order_by('-created_at')[:3]
        recent_portfolio_msgs = PortfolioMessage.objects.all().order_by('-created_at')[:2]
        
        messages_data = []
        for msg in recent_contact_msgs:
            messages_data.append({
                'type': 'contact',
                'id': msg.id,
                'name': msg.name,
                'preview': msg.message[:50] + '...' if len(msg.message) > 50 else msg.message,
                'created_at': msg.created_at.strftime("%Y-%m-%d %H:%M"),
                'is_read': msg.is_read
            })
        
        for msg in recent_portfolio_msgs:
            messages_data.append({
                'type': 'portfolio',
                'id': msg.id,
                'name': msg.name,
                'preview': msg.message[:50] + '...' if len(msg.message) > 50 else msg.message,
                'created_at': msg.created_at.strftime("%Y-%m-%d %H:%M"),
                'is_read': msg.is_read
            })
        
        return JsonResponse({
            "success": True,
            "data": {
                "products": products_data,
                "apps": apps_data,
                "demos": demos_data,
                "orders": orders_data,
                "messages": messages_data
            }
        }, status=200)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)



# ============================================================================
# Admin API Endpoints (AJAX for Dashboard)
# ============================================================================

# Dashboard Statistics
@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_dashboard_stats(request):
    """Get dashboard statistics via AJAX"""
    try:
        # Calculate stats
        stats = {
            'total_products': Product.objects.count(),
            'published_products': Product.objects.filter(status='published').count(),
            'draft_products': Product.objects.filter(status='draft').count(),
            'archived_products': Product.objects.filter(status='archived').count(),
            'categories_count': ProductCategory.objects.count(),
            'active_categories': ProductCategory.objects.filter(is_active=True).count(),
            'demo_requests_count': DemoRequest.objects.count(),
            'pending_demos': DemoRequest.objects.filter(status='pending').count(),
            'contacted_demos': DemoRequest.objects.filter(status='contacted').count(),
            'completed_demos': DemoRequest.objects.filter(status='completed').count(),
            'total_orders': Order.objects.count(),
            'pending_orders': Order.objects.filter(status='pending').count(),
            'processing_orders': Order.objects.filter(status='processing').count(),
            'completed_orders': Order.objects.filter(status='completed').count(),
            'cancelled_orders': Order.objects.filter(status='cancelled').count(),
            'revenue_total': str(Order.objects.filter(status='completed').aggregate(
                total=Sum('total')
            )['total'] or 0),
            'unread_contacts': ContactMessage.objects.filter(is_read=False).count(),
            'unread_portfolio': PortfolioMessage.objects.filter(is_read=False).count(),
            'total_messages': ContactMessage.objects.count() + PortfolioMessage.objects.count(),
        }
        
        # Recent activity (last 24 hours)
        yesterday = timezone.now() - timedelta(days=1)
        
        recent_products = Product.objects.filter(created_at__gte=yesterday).count()
        recent_orders = Order.objects.filter(created_at__gte=yesterday).count()
        recent_demos = DemoRequest.objects.filter(requested_at__gte=yesterday).count()
        
        stats.update({
            'recent_products': recent_products,
            'recent_orders': recent_orders,
            'recent_demos': recent_demos,
        })
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# Dashboard Refresh
@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def refresh_dashboard(request):
    """Refresh all dashboard data via AJAX"""
    try:
        # Get latest data for each section
        data = {
            'products': [],
            'categories': [],
            'demos': [],
            'orders': [],
            'messages': [],
        }
        
        # Products (last 5)
        products = Product.objects.all().select_related('category').order_by('-created_at')[:5]
        for product in products:
            data['products'].append({
                'id': product.id,
                'name': product.name,
                'category': product.category.name,
                'status': product.status,
                'price': str(product.price),
                'created_at': product.created_at.strftime('%H:%M'),
            })
        
        # Categories (last 5)
        categories = ProductCategory.objects.all().order_by('-created_at')[:5]
        for category in categories:
            data['categories'].append({
                'id': category.id,
                'name': category.name,
                'type': category.category_type,
                'product_count': category.product_count,
                'created_at': category.created_at.strftime('%H:%M'),
            })
        
        # Demo requests (last 5)
        demos = DemoRequest.objects.all().select_related('product').order_by('-requested_at')[:5]
        for demo in demos:
            data['demos'].append({
                'id': demo.id,
                'name': demo.full_name,
                'product': demo.product.name if demo.product else 'General',
                'status': demo.status,
                'requested_at': demo.requested_at.strftime('%H:%M'),
            })
        
        # Orders (last 5)
        orders = Order.objects.all().order_by('-created_at')[:5]
        for order in orders:
            data['orders'].append({
                'id': order.id,
                'order_number': order.order_number,
                'customer': order.customer_name,
                'total': str(order.total),
                'status': order.status,
                'created_at': order.created_at.strftime('%H:%M'),
            })
        
        # Messages (last 6 unread)
        messages = list(ContactMessage.objects.filter(is_read=False).order_by('-created_at')[:3])
        messages += list(PortfolioMessage.objects.filter(is_read=False).order_by('-submitted_at')[:3])
        
        for msg in messages:
            if hasattr(msg, 'submitted_at'):
                msg_type = 'portfolio'
                created_at = msg.submitted_at
            else:
                msg_type = 'contact'
                created_at = msg.created_at
            
            data['messages'].append({
                'id': msg.id,
                'type': msg_type,
                'name': msg.name,
                'email': msg.email,
                'preview': (msg.message[:30] + '...') if len(msg.message) > 30 else msg.message,
                'created_at': created_at.strftime('%H:%M'),
            })
        
        return JsonResponse({
            'success': True,
            'data': data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# ============================================================================
# Product Management (AJAX)
# ============================================================================
@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def create_product(request):
    """Create product via AJAX"""
    try:
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            
            # Generate slug if not provided
            if not product.slug:
                from django.utils.text import slugify
                product.slug = slugify(product.name)
                # Ensure unique slug
                original_slug = product.slug
                counter = 1
                while Product.objects.filter(slug=product.slug).exists():
                    product.slug = f"{original_slug}-{counter}"
                    counter += 1
            
            # Set published date if published
            if product.status == 'published' and not product.published_at:
                product.published_at = timezone.now()
            
            product.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Product created successfully!',
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'category': product.category.name if product.category else '',
                    'category_id': product.category.id if product.category else '',
                    'price': str(product.price),
                    'status': product.status,
                    'image_url': product.image.url if product.image else '/static/images/default-product.jpg',
                    'is_featured': product.is_featured,
                    'has_discount': product.has_discount,
                    'current_price': str(product.current_price),
                }
            })
        else:
            errors = {field: [str(err) for err in error_list] for field, error_list in form.errors.items()}
            return JsonResponse({
                'success': False,
                'errors': errors,
                'error_message': 'Please correct the errors below.'
            }, status=400)
            
    except Exception as e:
        import traceback
        print(f"Error creating product: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_message': 'An unexpected error occurred. Please try again.'
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["POST"])
def edit_product(request, product_id):
    """Edit product via AJAX"""
    try:
        product = get_object_or_404(Product, id=product_id)
        form = ProductForm(request.POST, request.FILES, instance=product)
        
        if form.is_valid():
            product = form.save(commit=False)
            
            # Update published_at if status changed to published
            if product.status == 'published' and not product.published_at:
                product.published_at = timezone.now()
            elif product.status != 'published':
                product.published_at = None
            
            product.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Product updated successfully!',
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'category': product.category.name,
                    'price': str(product.price),
                    'status': product.status,
                    'is_featured': product.is_featured,
                    'has_discount': product.has_discount,
                    'current_price': str(product.current_price),
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_product(request, product_id):
    """Delete product via AJAX"""
    try:
        product = get_object_or_404(Product, id=product_id)
        product.delete()
        return JsonResponse({
            'success': True,
            'message': 'Product deleted successfully!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_product(request, product_id):
    """Get product details for editing via AJAX"""
    try:
        product = get_object_or_404(Product, id=product_id)
        return JsonResponse({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'category_id': product.category.id,
                'description': product.description,
                'short_description': product.short_description,
                'price': str(product.price),
                'discount_price': str(product.discount_price) if product.discount_price else None,
                'display_order': product.display_order,
                'is_featured': product.is_featured,
                'status': product.status,
                'specifications': product.specifications,
                'image_url': product.image.url if product.image else '',
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_all_products(request):
    """Get all products for table via AJAX"""
    try:
        products = Product.objects.all().select_related('category').order_by('-created_at')
        product_list = []
        
        for product in products:
            product_list.append({
                'id': product.id,
                'name': product.name,
                'category': product.category.name,
                'category_type': product.category.category_type,
                'price': str(product.price),
                'discount_price': str(product.discount_price) if product.discount_price else None,
                'status': product.status,
                'is_featured': product.is_featured,
                'image_url': product.image.url if product.image else '',
                'created_at': product.created_at.strftime('%Y-%m-%d %H:%M'),
            })
        
        return JsonResponse({
            'success': True,
            'products': product_list,
            'total': len(product_list)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# ============================================================================
# Category Management (AJAX)
# ============================================================================

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["POST"])
def create_category(request):
    """Create category via AJAX"""
    try:
        data = json.loads(request.body)
        
        # Check for duplicate
        if ProductCategory.objects.filter(
            name=data.get('name'), 
            category_type=data.get('category_type')
        ).exists():
            return JsonResponse({
                'success': False,
                'error': 'A category with this name and type already exists!'
            })
        
        category = ProductCategory.objects.create(
            name=data.get('name'),
            category_type=data.get('category_type'),
            display_order=data.get('display_order', 0),
            is_active=data.get('is_active', True)
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Category created successfully!',
            'category': {
                'id': category.id,
                'name': category.name,
                'category_type': category.category_type,
                'display_order': category.display_order,
                'is_active': category.is_active,
                'product_count': 0
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["POST"])
def edit_category(request, category_id):
    """Edit category via AJAX"""
    try:
        category = get_object_or_404(ProductCategory, id=category_id)
        data = json.loads(request.body)
        
        # Check for duplicate (excluding current category)
        if ProductCategory.objects.filter(
            name=data.get('name'), 
            category_type=data.get('category_type')
        ).exclude(id=category_id).exists():
            return JsonResponse({
                'success': False,
                'error': 'A category with this name and type already exists!'
            })
        
        category.name = data.get('name', category.name)
        category.category_type = data.get('category_type', category.category_type)
        category.display_order = data.get('display_order', category.display_order)
        category.is_active = data.get('is_active', category.is_active)
        category.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Category updated successfully!',
            'category': {
                'id': category.id,
                'name': category.name,
                'category_type': category.category_type,
                'display_order': category.display_order,
                'is_active': category.is_active,
                'product_count': category.product_count
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_category(request, category_id):
    """Delete category via AJAX"""
    try:
        category = get_object_or_404(ProductCategory, id=category_id)
        category.delete()
        return JsonResponse({
            'success': True,
            'message': 'Category deleted successfully!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_category(request, category_id):
    """Get category details for editing via AJAX"""
    try:
        category = get_object_or_404(ProductCategory, id=category_id)
        return JsonResponse({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'category_type': category.category_type,
                'display_order': category.display_order,
                'is_active': category.is_active,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_all_categories(request):
    """Get all categories for table via AJAX"""
    try:
        categories = ProductCategory.objects.all().order_by('display_order', 'name')
        category_list = []
        
        for category in categories:
            category_list.append({
                'id': category.id,
                'name': category.name,
                'category_type': category.category_type,
                'display_order': category.display_order,
                'is_active': category.is_active,
                'product_count': category.product_count,
                'created_at': category.created_at.strftime('%Y-%m-%d'),
            })
        
        return JsonResponse({
            'success': True,
            'categories': category_list,
            'total': len(category_list)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# ============================================================================
# Site Configuration (AJAX)
# ============================================================================

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_site_config(request):
    """Get site configuration via AJAX"""
    try:
        config = SiteConfig.objects.filter(is_active=True).first()
        if not config:
            config = SiteConfig.objects.create()
        
        return JsonResponse({
            'success': True,
            'config': {
                'id': config.id,
                'site_name': config.site_name,
                'site_email': config.site_email,
                'currency': config.currency,
                'currency_symbol': config.currency_symbol,
                'is_active': config.is_active,
                'updated_at': config.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["POST"])
def update_site_config(request):
    """Update site configuration via AJAX"""
    try:
        data = json.loads(request.body)
        config = SiteConfig.objects.filter(is_active=True).first()
        
        if not config:
            config = SiteConfig.objects.create()
        
        config.site_name = data.get('site_name', config.site_name)
        config.site_email = data.get('site_email', config.site_email)
        config.currency = data.get('currency', config.currency)
        
        # Set currency symbol based on currency
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'KES': 'KSh',
            'INR': '₹',
            'CNY': '¥',
        }
        
        if data.get('currency_symbol'):
            config.currency_symbol = data['currency_symbol']
        elif config.currency in currency_symbols:
            config.currency_symbol = currency_symbols[config.currency]
        else:
            config.currency_symbol = '$'
        
        config.is_active = True
        config.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Site configuration updated successfully!',
            'config': {
                'id': config.id,
                'site_name': config.site_name,
                'currency_symbol': config.currency_symbol,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def get_currency_symbol(request):
    """API endpoint to get current currency symbol"""
    try:
        config = SiteConfig.objects.get(is_active=True)
        return JsonResponse({
            'currency': config.currency,
            'symbol': config.currency_symbol,
        })
    except SiteConfig.DoesNotExist:
        return JsonResponse({
            'currency': 'USD',
            'symbol': '$',
        })

# ============================================================================
# Demo Requests Management (AJAX)
# ============================================================================

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_all_demos(request):
    """Get all demo requests via AJAX"""
    try:
        status_filter = request.GET.get('status', '')
        demos = DemoRequest.objects.all().select_related('product').order_by('-requested_at')
        
        if status_filter:
            demos = demos.filter(status=status_filter)
        
        demo_list = []
        for demo in demos:
            demo_list.append({
                'id': demo.id,
                'full_name': demo.full_name,
                'email': demo.email,
                'phone': demo.phone or '',
                'company': demo.company or '',
                'product': demo.product.name if demo.product else 'General Inquiry',
                'status': demo.status,
                'requested_at': demo.requested_at.strftime('%Y-%m-%d %H:%M'),
                'message_preview': (demo.message[:50] + '...') if demo.message else '',
            })
        
        return JsonResponse({
            'success': True,
            'demos': demo_list,
            'total': len(demo_list),
            'pending_count': DemoRequest.objects.filter(status='pending').count()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["POST"])
def update_demo_status(request, demo_id):
    """Update demo request status via AJAX"""
    try:
        data = json.loads(request.body)
        demo = get_object_or_404(DemoRequest, id=demo_id)
        
        new_status = data.get('status')
        if new_status in dict(DemoRequest.STATUS_CHOICES).keys():
            demo.status = new_status
            
            if new_status == 'contacted' and not demo.contacted_at:
                demo.contacted_at = timezone.now()
            
            demo.notes = data.get('notes', demo.notes)
            demo.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Demo request status updated to {new_status}',
                'demo': {
                    'id': demo.id,
                    'status': demo.status,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid status'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_demo(request, demo_id):
    """Delete demo request via AJAX"""
    try:
        demo = get_object_or_404(DemoRequest, id=demo_id)
        demo.delete()
        return JsonResponse({
            'success': True,
            'message': 'Demo request deleted successfully!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_demo_details(request, demo_id):
    """Get demo request details via AJAX"""
    try:
        demo = get_object_or_404(DemoRequest, id=demo_id)
        
        return JsonResponse({
            'success': True,
            'demo': {
                'id': demo.id,
                'full_name': demo.full_name,
                'email': demo.email,
                'phone': demo.phone,
                'company': demo.company,
                'product': demo.product.name if demo.product else 'General Inquiry',
                'product_id': demo.product.id if demo.product else None,
                'interest_area': demo.interest_area,
                'message': demo.message,
                'status': demo.status,
                'notes': demo.notes,
                'requested_at': demo.requested_at.strftime('%Y-%m-%d %H:%M:%S'),
                'contacted_at': demo.contacted_at.strftime('%Y-%m-%d %H:%M:%S') if demo.contacted_at else '',
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["GET"])
def api_demo_detail(request, demo_id):
    """API endpoint for single demo request detail (public)"""
    try:
        demo = get_object_or_404(DemoRequest, id=demo_id)
        data = {
            'id': demo.id,
            'full_name': demo.full_name,
            'email': demo.email,
            'phone': demo.phone,
            'company': demo.company,
            'product_name': demo.product.name if demo.product else None,
            'interest_area': demo.interest_area,
            'message': demo.message,
            'status': demo.status,
            'notes': demo.notes,
            'requested_at': demo.requested_at.isoformat(),
        }
        return JsonResponse(data)
    except DemoRequest.DoesNotExist:
        return JsonResponse({'error': 'Demo request not found'}, status=404)

# ============================================================================
# Orders Management (AJAX)
# ============================================================================

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_all_orders(request):
    """Get all orders via AJAX"""
    try:
        status_filter = request.GET.get('status', '')
        orders = Order.objects.all().order_by('-created_at')
        
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        order_list = []
        for order in orders:
            order_list.append({
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'customer_email': order.customer_email,
                'total': str(order.total),
                'status': order.status,
                'payment_status': order.payment_status,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
                'item_count': order.orderitem_set.count(),
            })
        
        return JsonResponse({
            'success': True,
            'orders': order_list,
            'total': len(order_list),
            'total_revenue': str(Order.objects.aggregate(Sum('total'))['total__sum'] or 0)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["POST"])
def update_order_status(request, order_id):
    """Update order status via AJAX"""
    try:
        data = json.loads(request.body)
        order = get_object_or_404(Order, id=order_id)
        
        new_status = data.get('status')
        if new_status in dict(Order.ORDER_STATUS).keys():
            order.status = new_status
            order.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Order status updated to {new_status}',
                'order': {
                    'id': order.id,
                    'status': order.status,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid status'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_order_details(request, order_id):
    """Get order details via AJAX"""
    try:
        order = get_object_or_404(Order, id=order_id)
        items = order.orderitem_set.select_related('product')
        
        item_list = []
        for item in items:
            item_list.append({
                'product_name': item.product.name,
                'quantity': item.quantity,
                'price': str(item.price),
                'total': str(item.quantity * item.price),
            })
        
        return JsonResponse({
            'success': True,
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'customer_email': order.customer_email,
                'customer_phone': order.customer_phone,
                'customer_address': order.customer_address,
                'subtotal': str(order.subtotal),
                'tax': str(order.tax),
                'total': str(order.total),
                'status': order.status,
                'payment_method': order.payment_method,
                'payment_status': order.payment_status,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'items': item_list,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# ============================================================================
# Messages Management (AJAX)
# ============================================================================

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_all_messages(request):
    """Get all messages via AJAX"""
    try:
        contact_messages = ContactMessage.objects.all().order_by('-created_at')
        portfolio_messages = PortfolioMessage.objects.all().order_by('-submitted_at')
        
        messages_list = []
        
        # Contact messages
        for msg in contact_messages:
            messages_list.append({
                'id': msg.id,
                'type': 'contact',
                'name': msg.name,
                'email': msg.email,
                'message_preview': (msg.message[:50] + '...') if msg.message else '',
                'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M'),
                'is_read': msg.is_read,
            })
        
        # Portfolio messages
        for msg in portfolio_messages:
            messages_list.append({
                'id': msg.id,
                'type': 'portfolio',
                'name': msg.name,
                'email': msg.email,
                'message_preview': (msg.message[:50] + '...') if msg.message else '',
                'created_at': msg.submitted_at.strftime('%Y-%m-%d %H:%M'),
                'is_read': msg.is_read,
            })
        
        # Sort by date
        messages_list.sort(key=lambda x: x['created_at'], reverse=True)
        
        return JsonResponse({
            'success': True,
            'messages': messages_list[:50],  # Limit to 50
            'total': len(messages_list),
            'unread_count': ContactMessage.objects.filter(is_read=False).count() + 
                          PortfolioMessage.objects.filter(is_read=False).count()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["POST"])
def mark_message_read(request, message_type, message_id):
    """Mark message as read via AJAX"""
    try:
        if message_type == 'contact':
            message = get_object_or_404(ContactMessage, id=message_id)
        elif message_type == 'portfolio':
            message = get_object_or_404(PortfolioMessage, id=message_id)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid message type'
            })
        
        message.is_read = True
        message.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Message marked as read'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_message(request, message_type, message_id):
    """Delete message via AJAX"""
    try:
        if message_type == 'contact':
            message = get_object_or_404(ContactMessage, id=message_id)
        elif message_type == 'portfolio':
            message = get_object_or_404(PortfolioMessage, id=message_id)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid message type'
            })
        
        message.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Message deleted successfully!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["POST"])
def clear_all_messages(request):
    """Clear all messages via AJAX"""
    try:
        ContactMessage.objects.all().delete()
        PortfolioMessage.objects.all().delete()
        
        return JsonResponse({
            'success': True,
            'message': 'All messages cleared successfully!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_message_details(request, message_type, message_id):
    """Get message details via AJAX"""
    try:
        if message_type == 'contact':
            message = get_object_or_404(ContactMessage, id=message_id)
        elif message_type == 'portfolio':
            message = get_object_or_404(PortfolioMessage, id=message_id)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid message type'
            })
        
        # Mark as read
        message.is_read = True
        message.save()
        
        return JsonResponse({
            'success': True,
            'message': {
                'type': message_type,
                'id': message.id,
                'name': message.name,
                'email': message.email,
                'message': message.message,
                'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(message, 'created_at') 
                          else message.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_read': message.is_read,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# ============================================================================
# Additional API Endpoints (Public)
# ============================================================================

@require_http_methods(["GET"])
def api_product_detail(request, product_id):
    """API endpoint for single product detail"""
    try:
        product = Product.objects.get(id=product_id)
        data = {
            'id': product.id,
            'name': product.name,
            'category_id': product.category.id,
            'description': product.description,
            'short_description': product.short_description,
            'price': str(product.price),
            'discount_price': str(product.discount_price) if product.discount_price else None,
            'display_order': product.display_order,
            'specifications': product.specifications,
            'is_featured': product.is_featured,
            'status': product.status,
            'image_url': product.image.url if product.image else '',
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

@require_http_methods(["GET"])
def api_category_detail(request, category_id):
    """API endpoint for single category detail"""
    try:
        category = ProductCategory.objects.get(id=category_id)
        data = {
            'id': category.id,
            'name': category.name,
            'category_type': category.category_type,
            'display_order': category.display_order,
            'is_active': category.is_active,
        }
        return JsonResponse(data)
    except ProductCategory.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)

# ============================================================================
# Legacy Views (For compatibility - redirect to new AJAX system)
# ============================================================================

@login_required
@user_passes_test(is_admin)
def admin_messages(request):
    """Legacy: View all contact messages - redirects to dashboard"""
    django_messages.info(request, 'Use the Messages section in the dashboard')
    return redirect('admin_dashboard')

@login_required
@user_passes_test(is_admin)
def message_detail(request, message_type, message_id):
    """Legacy: View message detail - uses AJAX system"""
    # This will be handled by AJAX in the dashboard
    return redirect('admin_dashboard')

@login_required
@user_passes_test(is_admin)
def demo_requests(request):
    """Legacy: View all demo requests - redirects to dashboard"""
    django_messages.info(request, 'Use the Demo Requests section in the dashboard')
    return redirect('admin_dashboard')

@login_required
@user_passes_test(is_admin)
def admin_orders(request):
    """Legacy: View all orders - redirects to dashboard"""
    django_messages.info(request, 'Use the Orders section in the dashboard')
    return redirect('admin_dashboard')

@login_required
@user_passes_test(is_admin)
def portfolio_messages(request):
    """Legacy: View portfolio messages - redirects to dashboard"""
    django_messages.info(request, 'Use the Messages section in the dashboard')
    return redirect('admin_dashboard')

# ============================================================================
# Site Configuration Page (Legacy - now handled in dashboard)
# ============================================================================

@login_required
@user_passes_test(is_admin)
def site_config(request):
    """Site configuration management (legacy page)"""
    try:
        config = SiteConfig.objects.get(is_active=True)
    except SiteConfig.DoesNotExist:
        config = None
    
    if request.method == 'POST':
        form = SiteConfigForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save(commit=False)
            if config.currency == 'CUSTOM':
                # Keep the custom symbol
                pass
            else:
                # Set standard symbol based on currency
                symbols = {
                    'USD': '$',
                    'EUR': '€',
                    'GBP': '£',
                    'KES': 'KSh',
                    'INR': '₹',
                    'CNY': '¥',
                }
                config.currency_symbol = symbols.get(config.currency, '$')
            
            config.is_active = True  # Ensure it's active
            config.save()
            django_messages.success(request, 'Site configuration updated successfully!')
            return redirect('admin_dashboard')
    else:
        form = SiteConfigForm(instance=config)
    
    return render(request, 'admin/site_config.html', {
        'form': form,
        'config': config,
    })

#=============================================================samuel kibunja profile views=============================================================
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import ContactMessage


# Base styling with spinner and styled button
BASE_STYLE = """
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0f0f0f;
            color: #eee;
            text-align: center;
            padding: 40px;
            margin: 0;
        }
        h1 {
            color: #08c5ff;
            animation: spin 4s linear infinite;
            font-size: 2.2em;
            margin-bottom: 20px;
        }
        p, li {
            font-size: 1.1em;
            line-height: 1.6;
        }
        ul {
            list-style: none;
            padding: 0;
            margin: 20px auto;
            max-width: 600px;
        }
        li {
            padding: 6px;
        }
        .spinner {
            margin: 20px auto;
            height: 40px;
            width: 40px;
            border: 4px solid #08c5ff;
            border-top: 4px solid transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .btn {
            display: inline-block;
            margin-top: 30px;
            padding: 12px 28px;
            font-weight: bold;
            background: linear-gradient(145deg, #08c5ff, #0ee066);
            color: #000;
            border-radius: 8px;
            transition: 0.3s ease-in-out;
            box-shadow: 0 4px 10px rgba(8, 197, 255, 0.3);
            text-decoration: none;
        }
        .btn:hover {
            transform: scale(1.05);
            background: linear-gradient(145deg, #0ee066, #08c5ff);
            color: #fff;
        }

        /* Responsive behavior */
        @media (max-width: 600px) {
            body {
                padding: 20px;
            }
            h1 {
                font-size: 1.7em;
            }
            p, li {
                font-size: 1em;
            }
            .btn {
                padding: 10px 20px;
                font-size: 1em;
            }
        }
    </style>
    <div class="spinner"></div>
"""


RETURN_HOME_BUTTON = '<a href="/" class="btn">Return Home</a>'
def download_app(request):
    return render(request, "download.html")

from django.shortcuts import render, redirect
from .models import PortfolioMessage

def portifolio(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Save to database
        PortfolioMessage.objects.create(name=name, email=email, message=message)
        return redirect('portifolio')

    return render(request, 'portifolio.html')

# app_name/views.py
from django.shortcuts import render
from .models import PortfolioMessage

def portfolio_messages(request):
    # Fetch all messages, newest first
    messages = PortfolioMessage.objects.all().order_by('-submitted_at')
    return render(request, 'portifolio_messages.html', {'messages': messages})


def personal_profile(request):
    html = f"""
    <html><head><title>Samuel Kibunja - Profile</title>{BASE_STYLE}</head>
    <body>
        <h1>Samuel Kibunja (Dravis55)</h1>
        <p>Hi, I'm <strong>Macharia Samuel Kibunja</strong>, a passionate Full-Stack Developer with expertise in Django, React, cybersecurity, and AI.</p>
        <p>CEO & Co-Founder of <strong>DravTech Group of Companies</strong>.</p>
        <p>Currently a <strong>Data Analyst at KEPSA</strong>.</p>
        <p>Holds BSc in Computer Science from <strong>Chuka University</strong>.</p>
        {RETURN_HOME_BUTTON}
    </body></html>
    """
    return HttpResponse(html)


def education(request):
    html = f"""
    <html><head><title>Education</title>{BASE_STYLE}</head>
    <body>
        <h1>Education</h1>
        <p><strong>Kamunganga Primary School</strong> — KCPE: B+</p>
        <p><strong>Ichagaki Boys High School</strong></p>
        <p><strong>Karega Secondary School</strong> — KCSE: B+</p>
        <p><strong>Chuka University</strong> — BSc Computer Science</p>
        {RETURN_HOME_BUTTON}
    </body></html>
    """
    return HttpResponse(html)


def skills(request):
    html = f"""
    <html><head><title>Skills</title>{BASE_STYLE}</head>
    <body>
        <h1>Technical Skills</h1>
        <ul>
            <li>Languages: Python, JavaScript, TypeScript, C++, C#, SQL</li>
            <li>Backend: Django, DRF, FastAPI, PostgreSQL, MySQL</li>
            <li>Frontend: React.js, Next.js, Tailwind CSS, Redux</li>
            <li>Mobile Dev: React Native, Android (Java/Kotlin)</li>
            <li>Blockchain: Web3.js, Solidity</li>
            <li>Cybersecurity: Ethical Hacking</li>
            <li>AI: Machine Learning, Neural Networks</li>
            <li>Tools: Docker, Git, Linux, AWS, Firebase</li>
        </ul>
        {RETURN_HOME_BUTTON}
    </body></html>
    """
    return HttpResponse(html)


def experience(request):
    html = f"""
    <html><head><title>Experience</title>{BASE_STYLE}</head>
    <body>
        <h1>Work Experience</h1>
        <p><strong>Package Trainer</strong> at Gigs Cyber</p>
        <p><strong>Data Analyst</strong> at KEPSA (current)</p>
        <p><strong>CEO & Co-Founder</strong> at DravTech Group (startup)</p>
        {RETURN_HOME_BUTTON}
    </body></html>
    """
    return HttpResponse(html)


def projects(request):
    html = f"""
    <html><head><title>Projects</title>{BASE_STYLE}</head>
    <body>
        <h1>Projects</h1>
        <p>Explore my GitHub: <a href="https://github.com/dravis55" target="_blank">DRAVIS55</a></p>
        <ul>
            <li>JAVA-projects — Java templates</li>
            <li>django-web-development-basic-shoplenty — HTML shop template</li>
            <li>django-web-development-backend-basic — Django backend starter</li>
            <li>django-web-development-full-stack-development</li>
            <li>portal-django-website — Educational institution portal</li>
            <li>html-js-and-css-calculator — Simple web calculator</li>
        </ul>
        {RETURN_HOME_BUTTON}
    </body></html>
    """
    return HttpResponse(html)


def references(request):
    html = f"""
    <html><head><title>References</title>{BASE_STYLE}</head>
    <body>
        <h1>References</h1>
        <ul>
            <li><strong>Audrey Murigi</strong> – KEPSA</li>

        </ul>
        <p>Contact information available on request.</p>
        {RETURN_HOME_BUTTON}
    </body></html>
    """
    return HttpResponse(html)


def contact(request):
    html = f"""
    <html><head><title>Contact</title>{BASE_STYLE}</head>
    <body>
        <h1>Contact Information</h1>
        <p>Email: samuelkibunja55@gmail.com / dravislotum@gmail.com</p>
        <p>Phone: 0714026439 / 0758067458</p>
        <p>LinkedIn: <a href="https://www.linkedin.com/in/samuelkibunja" target="_blank">in/samuelkibunja</a></p>
        <p>Twitter: <a href="https://x.com/Dravis55" target="_blank">@Dravis55</a></p>
        {RETURN_HOME_BUTTON}
    </body></html>
    """
    return HttpResponse(html)


def about_us(request):
    html = f"""
    <html><head><title>About DravTech</title>{BASE_STYLE}</head>
    <body>
        <h1>About DravTech</h1>
        <p><strong>DravTech Group of Companies</strong> is a tech startup founded by Samuel Kibunja (Dravis).</p>
        <p>We aim to innovate in software development, AI, cybersecurity, and enterprise technology.</p>
        <p>Our solutions are smart, scalable, and tailored to clients' unique needs.</p>
        {RETURN_HOME_BUTTON}
    </body></html>
    """
    return HttpResponse(html)


from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render
from .models import ContactMessage
from django.conf import settings


def home(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        if name and email and message:
            # Save the message to DB
            ContactMessage.objects.create(
                name=name,
                email=email,
                message=message
            )

            # Send auto-reply email
            subject = "We've received your message"
            reply_message = f"""
Hi {name},

Thank you for contacting Dravtech!

We’ve received your message and our team is already reviewing it.
One of our representatives will get back to you as soon as possible.

Here’s a copy of your message for reference:
"{message}"

In the meantime, feel free to explore our website for more about our services:
https://dravis55.pythonanywhere.com

Best regards,
The Dravtech Support Team
"""

            try:
                send_mail(
                    subject,
                    reply_message,
                    settings.DEFAULT_FROM_EMAIL,  # Must be configured in settings.py
                    [email],
                    fail_silently=False,
                )
            except Exception as e:
                # You can log the error if needed
                print("Email sending failed:", e)

            return HttpResponse(f"""
<html>
<head>
    <title>Message Sent</title>
    {BASE_STYLE}
</head>
<body>
    <h2>Message Sent Successfully!</h2>
    <p>An automatic confirmation email has been sent to <b>{email}</b>.</p>
    {RETURN_HOME_BUTTON}
</body>
</html>
""")

    return render(request, "index.html")

def admin_messages(request):
    messages = ContactMessage.objects.all().order_by("-created_at")
    return render(request, "admin_messages.html", {"messages": messages})


def clear_messages(request):
    if request.method == "POST":
        ContactMessage.objects.all().delete()
        return redirect("admin_messages")



from django.shortcuts import render

from django.shortcuts import render

from django.shortcuts import render

def live(request):
    projects = [
        {'name': 'JAVA Projects', 'repo': 'JAVA-projects'},
        {'name': 'Shoplenty', 'repo': 'django-web-developmentbasic-shoplenty'},
        {'name': 'Backend Starter', 'repo': 'django-web-development-backend-basic'},
        {'name': 'Full‑Stack Starter', 'repo': 'django-web-development-full-stack-development'},
        {'name': 'Edu Portal', 'repo': 'portal-django-website'},
        {'name': 'Calculator', 'repo': 'html-js-and-css-calculator'},
    ]
    return render(request, 'lives.html', {'projects': projects})
def index(request):
    return render(request, 'about.html')

def videos(request):
    return render(request, 'video.html')