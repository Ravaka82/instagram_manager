from django.db import models

class InstagramUser(models.Model):
    username = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    bio_link = models.URLField(blank=True, null=True)
    is_master = models.BooleanField(default=False)

    class Meta:
        db_table = 'instagram_user'

    def __str__(self):
        return self.name

