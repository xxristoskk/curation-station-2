# from django import forms
from django.forms import ModelForm
from django import forms
from .models import Map, Profile
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class MapForm(ModelForm):
    class Meta:
        model = Map
        fields = ['country_region']

class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['bandcamp_username','spotify_username','sp_playlist_name','location']

class CreateUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']