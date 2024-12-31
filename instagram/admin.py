from django import forms
from django.utils.html import format_html
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from .models import InstagramUser, Publication
from instagram_manager import settings
from .core.instagram_service import InstagramService
import os
import requests
from django.core.files.storage import default_storage
from instagrapi import Client
from django.core.exceptions import ValidationError
from instagrapi.exceptions import ClientError, TwoFactorRequired
from tempfile import NamedTemporaryFile

@admin.register(InstagramUser)
class InstagramUserAdmin(admin.ModelAdmin):
    fields = ['username','password','name', 'profile_picture', 'bio', 'bio_link', 'is_master']
    list_display = ['username', 'name', 'password', 'is_master', 'profile_picture_display','sync_button','publish_button']
    actions = ['update_instagram_account','sync_instagram_account']

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
        return super().changelist_view(request, extra_context=extra_context)
    
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

    profile_picture_display.short_description = 'Profile Picture'

    def publish_button(self, obj):
        return format_html(
            '<a class="button" href="{}"> Faire une publication </a>',
            reverse('admin:publication_content_form', args=[obj.id])
        )

    publish_button.short_description = 'Publier la publication'
    publish_button.allow_tags = True

    def publication_content_form(self, request, user_id=None):
        try:
            instagram_user = InstagramUser.objects.get(id=user_id)
        except InstagramUser.DoesNotExist:
            self.message_user(request, "❌ Utilisateur Instagram introuvable.", level=messages.ERROR)
            return HttpResponseRedirect('..')

        if request.method == 'POST':
            content = request.POST.get('content')
            image = request.FILES.get('image')

            if not image:
                self.message_user(request, "❌ Aucune image sélectionnée.", level=messages.ERROR)
                return HttpResponseRedirect('..')

            file_path = os.path.join('media/uploads/', image.name)
            try:
                with open(file_path, 'wb') as f:
                    for chunk in image.chunks():
                        f.write(chunk)
            except Exception as e:
                self.message_user(request, f"❌ Impossible de sauvegarder l'image : {str(e)}", level=messages.ERROR)
                return HttpResponseRedirect('..')

            instagram_service = InstagramService()
            try:
                instagram_service.publish_post(instagram_user, content, content, file_path)
                self.message_user(request, "✅ Publication réussie!", level=messages.SUCCESS)
                os.remove(file_path) 
            except Exception as e:
                self.message_user(request, f"❌ Erreur lors de la publication : {str(e)}", level=messages.ERROR)
                os.remove(file_path)

            return HttpResponseRedirect('..')

        return render(request, 'admin/publication_content_form.html', {
            'instagram_user': instagram_user
        })

      
  
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
            self.message_user(request, f"✅ Compte Instagram '{obj.username}' mis à jour avec succès.", level=messages.SUCCESS)
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
                self.message_user(request, f"✅ Compte Instagram '{obj.username}' mis à jour avec succès.", level=messages.SUCCESS)
            except ValidationError as e:
                self.message_user(request, f"❌ Erreur : {e.message}", level=messages.ERROR)
            except Exception as e:
                self.message_user(request, "❌ Une erreur inattendue est survenue.", level=messages.ERROR)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('add_user_reel/', self.admin_site.admin_view(self.add_user_reel), name='add_user_reel'),
            path('publication_content_form/<int:user_id>/', self.admin_site.admin_view(self.publication_content_form), name='publication_content_form'),
            path('sync_instagram_account/<int:user_id>/', self.admin_site.admin_view(self.sync_instagram_account), name='sync_instagram_account'),
        
        ]
        return custom_urls + urls
    
    def sync_button(self, obj):
        print(f"Generating sync button for {obj.username}")  # Débogage
        if obj.is_master==True:
            return format_html(
                '<a class="button default" href="{}">Synchroniser 🔄​</a>',
                reverse('admin:sync_instagram_account', args=[obj.pk])
            )
        return "❌"
    sync_button.short_description = 'Synchronisation'
    
    def sync_instagram_account(self, request, user_id):
        user = InstagramUser.objects.get(pk=user_id)   
        #instagram_service = InstagramService()
        #result_sync = instagram_service.sync_account(user) 
        #if result_sync ==1:
            #self.message_user(request, f"✅ Instagram account '{user.username}' synchronized.", level=messages.SUCCESS)
        #else:
            #self.message_user(request, "❌ Une erreur de synchro inattendue est survenue.", level=messages.ERROR)

        non_master_users = InstagramUser.objects.filter(is_master=False)  # Récupérer les comptes non maîtres
    
        context = {
            'title': 'Synchronisation du compte Instagram',
            'compte_maitre': user,
            'compte_secondaire': non_master_users,
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
        }
        
        return render(request, 'admin/synchro.html', context)  

    

