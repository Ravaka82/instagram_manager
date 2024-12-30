from django import forms
from django.utils.html import format_html
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render

from instagram_manager import settings
from .models import InstagramUser
from .core.instagram_service import InstagramService

@admin.register(InstagramUser)
class InstagramUserAdmin(admin.ModelAdmin):
    fields = ['username','password','name', 'profile_picture', 'bio', 'bio_link', 'is_master']
    list_display = ['username', 'name','bio', 'is_master', 'profile_picture_display']
    actions = ['update_instagram_account']
    search_fields = ['name', 'username']

    def get_fields(self, request, obj=None):
        if obj is None: 
            return self.fields
        return [field for field in self.fields if field not in ['username', 'password']] 
    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial['is_master'] = True
        return initial
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['add_user_reel_link'] = reverse('admin:add_user_reel')
        return super().changelist_view(request, extra_context=extra_context)
    from django.utils.html import format_html

    def profile_picture_display(self, obj):
        if obj.profile_picture:
            image_url = str(obj.profile_picture)
            if image_url.startswith('http') or image_url.startswith('https'):
                return format_html(
                    '<img src="{}" style="border-radius: 50%; width: 50px; height: 50px;" />',
                    image_url
                )
            try:
                return format_html(
                    '<img src="{}" style="border-radius: 50%; width: 50px; height: 50px;" />',
                    obj.profile_picture.url
                )
            except ValueError:
                return "Invalid image URL"
        
        return "No image"
    profile_picture_display.short_description = 'Profil_picture'
  

    def add_user_reel(self, request):
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')
            otp = request.POST.get('otp')
            instagram_service = InstagramService()
            rep_User = instagram_service.authenticate(username, password, otp)
            if rep_User==1:
                self.message_user(request, f"✅ Instagram account '{username}' successfully created.", level=messages.SUCCESS)
            if rep_User==2:
                self.message_user(request, "❌ This Instagram account already exists in the application.", level=messages.ERROR)
            return HttpResponseRedirect('..')

        return render(request, 'admin/add_user_reel.html', {})

    
    def save_model(self, request, obj, form, change):
        service = InstagramService()
        try:
            super().save_model(request, obj, form, change)
            service.update_account(obj)
            self.message_user(request, f"✅ Instagram account '{obj.username}' successfully updated.", level=messages.SUCCESS)
        except ValidationError as e:
            self.message_user(request, f"❌ Erreur : {e.message}", level=messages.ERROR)
        except Exception as e:
            self.message_user(request, "❌ Une erreur inattendue est survenue.", level=messages.ERROR)

    @admin.action(description="Mettre à jour les comptes Instagram sélectionnés")
    def update_instagram_account(self, request, queryset):
        service = InstagramService()
        for obj in queryset:
            try:
                service.update_account(obj)
                self.message_user(request, f"✅ Instagram account '{obj.username}' successfully updated.", level=messages.SUCCESS)
            except ValidationError as e:
                self.message_user(request, f"❌ Erreur : {e.message}", level=messages.ERROR)
            except Exception as e:
                self.message_user(request, "❌ Une erreur inattendue est survenue.", level=messages.ERROR)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('add_user_reel/', self.admin_site.admin_view(self.add_user_reel), name='add_user_reel'),
        ]
        return custom_urls + urls
