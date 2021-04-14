from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from geopy.geocoders import Nominatim

# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(
        User, 
        # primary_key=True,
        on_delete=models.CASCADE,
    )
    bandcamp_username = models.CharField(max_length=100, null=True, blank=True)
    spotify_username = models.CharField(max_length=100, null=True, blank=True)
    spotify_token = models.CharField(max_length=200, null=True, blank=True)
    spotify_refresh = models.CharField(max_length=150, null=True, blank=True)
    token_exp = models.IntegerField(null=True, blank=True)
    sp_playlist_name = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude= models.FloatField(blank=True, null=True)

    def save(self, *args, **kwargs):
        geolocator = Nominatim(user_agent="CurationLab")
        loc = geolocator.geocode(self.location)
        if not self.location:
            return None
        else:
            self.latitude = loc.latitude
            self.longitude = loc.longitude
            return super(Profile, self).save(*args, **kwargs)


    def __str__(self):
        return self.user.username + " profile"