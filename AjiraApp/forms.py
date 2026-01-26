# forms.py - Updated with manual category type input
from django import forms
from .models import Product, ProductCategory, ProductImage, SiteConfig

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'short_description',
            'price', 'discount_price', 'image', 'display_order',
            'is_featured', 'status', 'specifications'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'short_description': forms.TextInput(attrs={'maxlength': 300}),
            'specifications': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter JSON specifications'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ProductCategory.objects.filter(is_active=True)

class CategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'category_type', 'display_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter category name'}),
            'category_type': forms.TextInput(attrs={
                'placeholder': 'Enter category type (e.g., System, Design, Software)',
                'list': 'category-type-suggestions'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get existing category types for suggestions
        existing_types = ProductCategory.objects.values_list('category_type', flat=True).distinct()
        self.fields['category_type'].widget.attrs.update({
            'data-suggestions': list(existing_types)
        })

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'display_order']
        widgets = {
            'alt_text': forms.TextInput(attrs={'placeholder': 'Enter alt text for accessibility'}),
        }

class SiteConfigForm(forms.ModelForm):
    class Meta:
        model = SiteConfig
        fields = ['site_name', 'site_email', 'currency', 'currency_symbol', 'is_active']
        widgets = {
            'currency_symbol': forms.TextInput(attrs={'maxlength': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add currency choices
        self.fields['currency'] = forms.ChoiceField(choices=[
            ('USD', 'US Dollar ($)'),
            ('EUR', 'Euro (€)'),
            ('GBP', 'British Pound (£)'),
            ('KES', 'Kenyan Shilling (KSh)'),
            ('INR', 'Indian Rupee (₹)'),
            ('CNY', 'Chinese Yuan (¥)'),
            ('CUSTOM', 'Custom Currency'),
        ])