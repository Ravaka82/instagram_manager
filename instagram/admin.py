from django.utils.html import format_html
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from .models import InstagramUser, Publication
from .core.instagram_service import InstagramService
import os
import requests
from django.core.files.storage import default_storage
from instagrapi import Client
from django.core.exceptions import ValidationError
from instagrapi.exceptions import ClientError, TwoFactorRequired
from tempfile import NamedTemporaryFile


class InstagramUserAdmin(admin.ModelAdmin):
    fields = ['name', 'profile_picture', 'bio', 'bio_link', 'is_master']
    list_display = ['username', 'name', 'password', 'is_master', 'profile_picture_display', 'publish_button']
    actions = ['update_instagram_account']
    search_fields = ['name', 'username']

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        return super().changelist_view(request, extra_context=extra_context)

    def profile_picture_display(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="border-radius: 50%; width: 50px; height: 50px;" />',
                obj.profile_picture.url
            )
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
            if rep_User == 1:
                self.message_user(request, f"✅ Compte Instagram '{username}' créé avec succès.", level=messages.SUCCESS)
            elif rep_User == 2:
                self.message_user(request, "❌ Ce compte Instagram existe déjà dans l'application.", level=messages.ERROR)
            else:
                self.message_user(request, "❌ Le compte Instagram n'existe pas.", level=messages.ERROR)
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
        ]
        return custom_urls + urls
    
admin.site.register(InstagramUser, InstagramUserAdmin)
