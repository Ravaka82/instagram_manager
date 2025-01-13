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
    list_display = ['username', 'password', 'name', 'bio', 'is_master_display', 'is_master', 'profile_picture_display', 'sync_button', 'publish_button', 'show_publications_button']
    actions = ['update_instagram_account', 'sync_instagram_account']

    search_fields = ['name', 'username']
    def is_master_display(self,obj):
        if obj.is_master == True:
            return "Master Account"
        else:
            return "Secondary Account"
    is_master_display.short_description = 'Type of account'

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
            '<a class="button" href="{}"> Post 📝​</a>',
            reverse('admin:publication_content_form', args=[obj.id])
        )

    publish_button.short_description = 'Publish the post'
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
            schedule = request.POST.get('schedule')
            if not image:
                self.message_user(request, "❌ Aucune image sélectionnée.", level=messages.ERROR)
                return HttpResponseRedirect('..')
        

            instagram_service = InstagramService()
            try:
                
                result = instagram_service.publish_post(instagram_user, content, content, image,schedule)
                if result==1:
                    self.message_user(request, "✅ Publication success!", level=messages.SUCCESS)
                if result==0:
                    self.message_user(request, "❌ Publication failed!", level=messages.ERROR)
            except Exception as e:
                self.message_user(request, f"❌ Erreur lors de la publication : {str(e)}", level=messages.ERROR)
            return HttpResponseRedirect('..')
        return render(request, 'admin/publication_content_form.html', {
            'instagram_user': instagram_user
        })
    
    def show_publications(self, request, user_id):
        try:
            instagram_user = InstagramUser.objects.get(id=user_id)
            publications = Publication.objects.filter(instagram_user=instagram_user).order_by('-scheduled_at')
            published_publications = publications.filter(is_published=True)
            scheduled_publications = publications.filter(is_published=False)

        except InstagramUser.DoesNotExist:
            self.message_user(request, "❌ Instagram User not found.", level=messages.ERROR)
            return HttpResponseRedirect('..')

        return render(request, 'admin/show_publications.html', {
            'instagram_user': instagram_user,
            'published_publications': published_publications,
            'scheduled_publications': scheduled_publications,
        })


    def show_publications_button(self, obj):
        return format_html(
            '<a class="button" href="{}">Show Publications 📜</a>',
            reverse('admin:show_publications', args=[obj.id])
        )

    show_publications_button.short_description = 'Show Publications'
    show_publications_button.allow_tags = True

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
            if rep_User==3:
                self.message_user(request, "❌ Instagram account connection failed.Login or password incorrect", level=messages.ERROR)
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
            path('sync_selected_accounts/', self.admin_site.admin_view(self.sync_selected_accounts), name='sync_selected_accounts'),
            path('show_publications/<int:user_id>/', self.admin_site.admin_view(self.show_publications), name='show_publications'),
        ]
        return custom_urls + urls
    
    def sync_button(self, obj):
        if obj.is_master==True:
            return format_html(
                '<a class="button default" href="{}">Synchronize 🔄​</a>',
                reverse('admin:sync_instagram_account', args=[obj.pk])
            )
        return "❌"
    sync_button.short_description = 'Synchronization'
    
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
            'title': 'Instagram account synchronization',
            'compte_maitre': user,
            'compte_secondaire': non_master_users,
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
        }
        
        return render(request, 'admin/synchro.html', context)  
    def sync_selected_accounts(self, request):
        if request.method == 'POST':
            compte_maitre_id = request.POST.get('compte_maitre_id')
            selected_ids = request.POST.getlist('selected_accounts')
            instagram_service = InstagramService()
            result_sync = instagram_service.sync_account(compte_maitre_id,selected_ids) 
            if result_sync ==1:
                self.message_user(request, f"✅ Instagram account synchronized.", level=messages.SUCCESS)
            else:
                self.message_user(request, "❌ Une erreur de synchro inattendue est survenue.", level=messages.ERROR)
            #print("IDs sélectionnés :", selected_ids)  # Affiche les ID dans la console Django
            #self.message_user(request, f"✅ IDs sélectionnés : {', '.join(selected_ids)}", level=messages.SUCCESS)
        return HttpResponseRedirect('..')
    

