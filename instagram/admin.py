from django import forms
from django.contrib import admin
from django.utils.html import format_html  
from instagram.core.instagram_service import InstagramService
from .models import InstagramUser


class InstagramUserAdmin(admin.ModelAdmin):
    fields = ['name', 'profile_picture', 'bio', 'bio_link', 'is_master']
    list_display = ['username','name','password','is_master','profile_picture_display'] 
    search_fields = ['name','username']
    actions = ['update_instagram_account_action']


    def profile_picture_display(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="border-radius: 50%; width: 50px; height: 50px;" />', 
                obj.profile_picture.url  
            )
        return "Pas d'image"

    profile_picture_display.short_description = 'Profil_picture' 

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
            if change:  
                service = InstagramService()
                service.update_account(obj)
                self.message_user(request, f"Compte Instagram '{obj.name}' mis à jour avec succès.")
        except Exception as e:
            self.message_user(request, f"Erreur lors de la mise à jour Instagram pour '{obj.name}': {e}", level='error')

    def update_instagram_account_action(self, request, queryset):
        service = InstagramService()
        for instagram_user in queryset:
            try:
                print(f"Mise à jour de l'utilisateur Instagram : {instagram_user.name}")
                service.update_account(instagram_user)
            except Exception as e:
                self.message_user(request, f"Erreur avec {instagram_user.name} : {e}", level='error')

     
    update_instagram_account_action.short_description = "Mettre à jour les comptes Instagram"

admin.site.register(InstagramUser, InstagramUserAdmin)
