import os
from django.core.files.storage import default_storage
from instagrapi import Client
from django.core.exceptions import ValidationError

class InstagramService:
    def __init__(self):
        self.client = Client()

    def update_account(self, instagram_user):
        name_updated = False  
        profile_picture_updated = False  
        messageError=""
        try:
            print("🔑 Connexion à Instagram...")
            
            if instagram_user.profile_picture:
                profile_picture_path = default_storage.path(instagram_user.profile_picture.name)
                print(f"📸 Changement de la photo de profil depuis : {profile_picture_path}")
            else:
                profile_picture_path = None

            self.client.login(instagram_user.username, instagram_user.password)

            try:
                print("🛠️ Mise à jour du nom d'affichage...")
                self.client.account_edit(
                    full_name=instagram_user.name,
                    biography=instagram_user.bio,
                    external_url=instagram_user.bio_link
                )
                print("✅ Nom d'affichage, bio et lien mis à jour sur le compte réel Instagram.")
                name_updated = True 
            except Exception as e:
                if "You can't change your name right now" in str(e):
                    name_updated = False
                    print("⚠️ Impossible de changer le nom en raison de restrictions de fréquence de changement.")
                    messageError = "⚠️ Impossible de changer le nom en raison de restrictions de fréquence de changement. La restriction est souvent levée après 14 jours, donc vous pouvez réessayer plus tard."
                else:
                    raise ValidationError(f"⚠️ Erreur lors de la mise à jour du nom : {str(e)}")

            if profile_picture_path and os.path.exists(profile_picture_path):
                print(f"📸 Mise à jour de la photo de profil depuis : {profile_picture_path}")
                result = self.client.account_change_picture(profile_picture_path)
                if result:
                    print("✅ Photo de profil mise à jour avec succès.")
                    profile_picture_updated = True  
                else:
                    messageError = "❌ Échec du changement de la photo de profil."
                    raise ValidationError("❌ Échec du changement de la photo de profil.")
            else:
                raise ValidationError(f"❌ Le fichier '{profile_picture_path}' est introuvable.")

            if name_updated and profile_picture_updated:
                instagram_user.save()
                print("✅ Les informations du compte Instagram ont été mises à jour dans la base de données.")
            else:
                raise ValidationError(messageError)

        except ValidationError as e:
            print(f"⚠️ Erreur : {e}")
            raise e
        except Exception as e:
            raise ValidationError(f"⚠️ Erreur inattendue : {e}")
