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


class Publication(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    image = models.CharField(max_length=255, null=True, blank=True) 
    date_posted = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    instagram_user = models.ForeignKey(
        'InstagramUser', on_delete=models.CASCADE, related_name='publications'
    )

    def __str__(self):
        return self.title
