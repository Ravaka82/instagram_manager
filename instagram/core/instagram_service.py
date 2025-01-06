import os,io
import requests
from django.core.files.storage import default_storage
from instagrapi import Client
from django.core.exceptions import ValidationError
from instagrapi.exceptions import ClientError, TwoFactorRequired
from tempfile import NamedTemporaryFile
from instagram.models import InstagramUser,Publication
from django.core.files.base import ContentFile
from PIL import Image
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
            profile_picture_url = str(user_info.profile_pic_url)
            response = requests.get(profile_picture_url)
            if response.status_code == 200:
                image_name = profile_picture_url.split("/")[-1]
                max_length = 100
                if len(image_name) > max_length:
                    image_name = image_name[:max_length]
                try:
                    image = Image.open(io.BytesIO(response.content))
                    image.verify()  
                except (IOError, SyntaxError) as e:
                    print(f"Erreur : Fichier non valide ou non image. {e}")
                    return 4  
                image = Image.open(io.BytesIO(response.content))
                image = image.convert("RGB") 
                jpg_image_io = io.BytesIO()
                image.save(jpg_image_io, format="JPEG")
                jpg_image_io.seek(0) 
                image_file = ContentFile(jpg_image_io.read(), name=image_name.split('.')[0] + '.jpg')
                instagram_user = InstagramUser.objects.update_or_create(
                    username=user_info.username,
                    defaults={
                        "password": password,
                        "name": user_info.full_name,
                        "profile_picture": image_file,
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
            print("Erreur : Nom d'utilisateur ou mot de passe incorrect. ou bien compte incorrecte")
            return 3
        except Exception as e:
            print(f"Erreur générale : {e}")
            return 0

    def update_account(self, instagram_user):
        name_updated = False  
        profile_picture_updated = False  
        messageError = ""
        try:
            if instagram_user.is_master:
                print("🔒 L'utilisateur est marqué comme 'is_master'. Connexion à Instagram désactivée.")
                if instagram_user.profile_picture:
                    profile_picture_path = default_storage.path(instagram_user.profile_picture.name)
                    if os.path.exists(profile_picture_path):
                        print(f"📸 Mise à jour de la photo de profil depuis : {profile_picture_path}")
                        instagram_user.save()
                        profile_picture_updated = True  
                        print("✅ Photo de profil mise à jour avec succès pour l'utilisateur is_master.")
                    else:
                        print(f"❌ Le fichier local '{profile_picture_path}' est introuvable.")
                        raise ValidationError("❌ Impossible de trouver la photo de profil pour l'utilisateur is_master.")
                else:
                    print("⚠️ Aucune photo de profil à mettre à jour pour l'utilisateur is_master.")
                
                return {
                    "name_updated": name_updated,
                    "profile_picture_updated": profile_picture_updated,
                    "error_message": messageError
                }

            print("🔑 Connexion à Instagram...")

            profile_picture_path = None
            if instagram_user.profile_picture:
                profile_picture = instagram_user.profile_picture.name

                if profile_picture.startswith('http://') or profile_picture.startswith('https://'):
                    print(f"🌐 Téléchargement de la photo depuis l'URL : {profile_picture}")
                    try:
                        response = requests.get(profile_picture, stream=True)
                        response.raise_for_status()
                        with NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                            for chunk in response.iter_content(chunk_size=1024):
                                tmp_file.write(chunk)
                            profile_picture_path = tmp_file.name
                        print(f"✅ Photo téléchargée temporairement : {profile_picture_path}")
                    except requests.exceptions.RequestException as e:
                        raise ValidationError(f"❌ Erreur lors du téléchargement de la photo : {e}")
                else:
                    profile_picture_path = default_storage.path(profile_picture)
                    if os.path.exists(profile_picture_path):
                        print(f"📸 Changement de la photo de profil depuis le fichier local : {profile_picture_path}")
                    else:
                        print(f"❌ Le fichier local '{profile_picture_path}' est introuvable.")
                        profile_picture_path = None
            self.client.login(instagram_user.username, instagram_user.password)
            try:
                print("🛠️ Mise à jour du nom, bio et lien...")
                self.client.account_edit(
                    full_name=instagram_user.name,
                    biography=instagram_user.bio,
                    external_url=instagram_user.bio_link
                )
                print("✅ Nom, bio et lien mis à jour avec succès.")
                name_updated = True
            except Exception as e:
                if "You can't change your name right now" in str(e):
                    name_updated = False
                    print("⚠️ Impossible de changer le nom pour le moment en raison de restrictions de fréquence.")
                    messageError = "⚠️ Unable to change the name due to frequency restrictions."
                else:
                    raise ValidationError(f"⚠️ Error while updating the name: {str(e)}")

            if profile_picture_path:
                print(f"📸 Mise à jour de la photo de profil depuis : {profile_picture_path}")
                result = self.client.account_change_picture(profile_picture_path)

                if result:
                    print("✅ Photo de profil mise à jour avec succès.")
                    profile_picture_updated = True  
                else:
                    messageError = "❌ Failed to change the profile picture."
                    raise ValidationError("❌ Failed to change the profile picture.")
            else:
                print("⚠️ Aucune photo de profil à mettre à jour.")

            if name_updated or profile_picture_updated:
                clien_info = self.client.account_info()
                instagram_user.profile_picture = str(clien_info.profile_pic_url)
                instagram_user.save()
                print("✅ Les informations du compte Instagram ont été mises à jour dans la base de données.")
            else:
                raise ValidationError(messageError)

        except ValidationError as e:
            print(f"⚠️ Erreur de validation : {e}")
            raise e
        except Exception as e:
            print(f"❌ Erreur inattendue : {str(e)}")
            raise ValidationError(f"⚠️ Erreur inattendue : {e}")
        finally:
            if profile_picture_path and profile_picture_path.startswith('/tmp'):
                try:
                    os.remove(profile_picture_path)
                    print(f"🧹 Fichier temporaire supprimé : {profile_picture_path}")
                except OSError:
                    print(f"⚠️ Impossible de supprimer le fichier temporaire : {profile_picture_path}")

        return {
            "name_updated": name_updated,
            "profile_picture_updated": profile_picture_updated,
            "error_message": messageError
        }

    def publish_post(self, instagram_user, title, description, image_path):
        try:
            print("🔑 Connexion à Instagram...")
            self.client.login(instagram_user.username, instagram_user.password)
            if not os.path.exists(image_path):
                raise ValidationError("❌ Le fichier d'image spécifié est introuvable.")
            media = self.client.photo_upload(image_path, title)
            print("✅ Publication réussie !")
            publication = Publication(
                instagram_user=instagram_user,
                title=title,
                description=description,
                image=image_path,
                date_posted=media.taken_at, 
                is_published=True
            )
            publication.save()
            return True

        except Exception as e:
            print(f"Erreur lors de la publication : {e}")
            raise ValidationError(f"❌ Erreur de publication : {e}")

    def sync_account(self, compte_maitre_id, selected_ids):
        print(f"Compte maitre : {compte_maitre_id}")
        print(f"Synchronizing account for user: {selected_ids}")
        modification_reussie = False
        try:
            compte_maitre = InstagramUser.objects.get(id=compte_maitre_id)
            print("🔑 Verification sur Instagram...")
            i=0
            for i in range(len(selected_ids)):
                instagram_user = InstagramUser.objects.get(id=selected_ids[i])
                client = Client()
                user_secondaire = client.login(instagram_user.username, instagram_user.password)
                if user_secondaire:
                    try:
                        client.account_edit(
                            full_name=compte_maitre.name,
                            biography=compte_maitre.bio,
                            external_url=compte_maitre.bio_link
                        )
                        if compte_maitre.profile_picture:
                            profile_picture_path = default_storage.path(compte_maitre.profile_picture.name)
                            client.account_change_picture(profile_picture_path)
                        InstagramUser.objects.update_or_create(
                        id=instagram_user.id,
                        defaults={
                            "name": compte_maitre.name,
                            "profile_picture": str(compte_maitre.profile_picture),
                            "bio": compte_maitre.bio,
                            "bio_link": str(compte_maitre.bio_link),
                        })
                        #client.logout()
                        modification_reussie = True
                    except Exception as e:
                        error_message = str(e)
                        print(f"Erreur lors de la modification du nom : {error_message}")
                        if "changed it twice within 14 days" in error_message:
                            print("⚠️ Limitation détectée : Mise à jour uniquement de la biographie, du lien externe et de la photo de profil.")
                            client.account_edit(
                                biography=compte_maitre.bio,
                                external_url=compte_maitre.bio_link
                            )
                            if compte_maitre.profile_picture:
                                profile_picture_path = default_storage.path(compte_maitre.profile_picture.name)
                                client.account_change_picture(profile_picture_path)
                            InstagramUser.objects.update_or_create(
                            id=instagram_user.id,
                            defaults={
                                "name": compte_maitre.name,
                                "profile_picture": str(compte_maitre.profile_picture),
                                "bio": compte_maitre.bio,
                                "bio_link": str(compte_maitre.bio_link),
                            })
                            modification_reussie = True
                        else:
                            raise e
            
        except Exception as e:
            print("❌ Échec de la synchronisation.")
            print(f"Erreur: {str(e)}")
            return 0
        return 1 if modification_reussie else 0
