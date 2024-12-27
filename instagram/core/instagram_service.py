import os
from django.core.files.storage import default_storage
from instagrapi import Client
from django.core.exceptions import ValidationError
from instagrapi.exceptions import ClientError, TwoFactorRequired

from instagram.models import InstagramUser

class InstagramService:
    def __init__(self):
        self.client = Client()
  

    def authenticate(self, username, password, otp=None):
        try:
            existing_user = InstagramUser.objects.filter(username=username, password=password).first()
            if existing_user:
                print("🔑 Connexion avec un utilisateur existant...")
                return 2  
            
            print("🔑 Connexion à Instagram...")
            if otp:
                print("Étape : Connexion avec OTP")
                login_response = self.client.login(username, password, verification_code=otp)
                if not login_response:
                    raise ValueError("Échec de la connexion avec le code OTP")
            else:
                print("Étape : Connexion normale")
                self.client.login(username, password)

            user_info = self.client.account_info()
            InstagramUser.objects.update_or_create(
                    defaults={
                        "username": user_info.username,
                        "password": password,
                        "name": user_info.full_name,
                        "profile_picture": str(user_info.profile_pic_url),
                        "bio": user_info.biography,
                        "bio_link": str(user_info.external_url) if user_info.external_url else None,
                        "is_master": False,
                    }
            )
            print(f"Informations de l'utilisateur récupérées avec succès : {user_info}")
            return 1

        except TwoFactorRequired:
            print("Erreur : Code OTP requis ou incorrect.")
            return 0
        except ClientError:
            print("Erreur : Nom d'utilisateur ou mot de passe incorrect.")
            return 0
        except Exception as e:
            print(f"Erreur générale : {e}")
            return 0

        
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
                    messageError = "⚠️ Unable to change the name due to change frequency restrictions. The restriction is often lifted after 14 days, so you can try again later."
                else:
                    raise ValidationError(f"⚠️ Error while updating the name.: {str(e)}")

            if profile_picture_path and os.path.exists(profile_picture_path):
                print(f"📸 Mise à jour de la photo de profil depuis : {profile_picture_path}")
                result = self.client.account_change_picture(profile_picture_path)
                if result:
                    print("✅ Photo de profil mise à jour avec succès.")
                    profile_picture_updated = True  
                else:
                    messageError = "❌ Failed to change the profile picture."
                    raise ValidationError("❌ Failed to change the profile picture.")
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
