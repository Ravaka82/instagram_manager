from django.utils.html import format_html  
from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import InstagramUser
from .core.instagram_service import InstagramService

class InstagramUserAdmin(admin.ModelAdmin):
    fields = ['name', 'profile_picture', 'bio', 'bio_link', 'is_master']
    list_display = ['username','name','password','is_master','profile_picture_display'] 
    actions = ['update_instagram_account']
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
                self.message_user(request, f"✅ Compte '{obj.username}' mis à jour avec succès.", level=messages.SUCCESS)
            except ValidationError as e:
                self.message_user(request, f"❌ Erreur : {e.message}", level=messages.ERROR)
            except Exception as e:
                self.message_user(request, "❌ Une erreur inattendue est survenue.", level=messages.ERROR)

admin.site.register(InstagramUser, InstagramUserAdmin)
