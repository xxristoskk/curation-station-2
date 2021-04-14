from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.views import View

# rest framework imports
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

# app imports
from frontpage.models import Profile
from frontpage.forms import CreateUserForm, ProfileForm

# needed for refreshing spotify auth tokens
import time

# handling spotify auth
import spotipy
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyOAuth

# initializing the database connection
import pymongo
import os

mongodb_pw = os.environ['MONGODB_PW']
mongodb_user = os.environ['MONGODB_USER']


client = pymongo.MongoClient(f'mongodb+srv://{mongodb_user}:{mongodb_pw}@bc01-muwwi.gcp.mongodb.net/test?retryWrites=true&w=majority')
db = client.BC02
coll = db.artistInfo

# initialize global spotify variables
scope = 'playlist-modify-public'
client_id = os.environ['SPOTIFY_ID']
client_secret = os.environ['SPOTIFY_SECRET']
redirect_uri = 'https://curation-station-2.herokuapp.com/redirect/'

# spotipy defaults to storing cached tokens to a cache file
# this class inherits from the base cache handler so tokens are saved to the profile model
class CustomCacheHandler(CacheHandler):
    def __init__(self, user):
        self.user = user 
    
    def get_cached_token(self):
        token_info = None
        try:
            token_info = {
                'access_token': self.user.profile.spotify_token,
                'expires_at': self.user.profile.token_exp,
                'refresh_token': self.user.profile.spotify_refresh
            }
        except:
            print('No token info')
        return token_info
    
    def save_token_to_cache(self, token_info):
        try:
            self.user.profile.spotify_token = token_info['access_token']
            self.user.profile.token_exp = token_info['expires_at']
            self.user.profile.spotify_refresh = token_info['refresh_token']
            self.user.profile.save(update_fields=['spotify_token','spotify_refresh','token_exp'])
        except:
            print("Couldn't save token info")

## user login & creation
def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        form = CreateUserForm()
        if request.method == 'POST':
            form = CreateUserForm(request.POST)
            if form.is_valid():
                user = form.save()
                username = form.cleaned_data.get('username')
                Profile.objects.create(
                    user=user,
                )
                messages.success(request, f'User {username} has been created')

                return redirect('login')

        context = {'form': form}
        return render(request, 'register.html', context=context)

def loginPage(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        if request.method=='POST':
            username = request.POST.get('username')
            password = request.POST.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.info(request, 'Username or Password is incorrect')

        context = {}
        return render(request, 'login.html', context=context)

def logout_user(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def profile(request):
    user = request.user
    form = ProfileForm(
        initial={
            'bandcamp_username': user.profile.bandcamp_username,
            'spotify_username': user.profile.spotify_username,
            'sp_playlist_name': user.profile.sp_playlist_name,
            'location': user.profile.location
        },
        instance=user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated')
            return redirect('dashboard')

    context = {'form': form}
    return render(request, 'profile.html', context=context)

def landingpage(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    ## code for contact form
    context = {}
    return render(request, 'index.html', context)

@login_required(login_url='login')
def dashboard(request):
    token_exp = request.user.profile.token_exp
    sp_token = request.user.profile.spotify_token
    refresh_token = request.user.profile.spotify_refresh

    oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_handler=CustomCacheHandler(request.user),
        show_dialog=True
    )

    # check for spotify authorization and refresh token if needed
    now = int(time.time())
    if not token_exp or not sp_token:
        is_valid = False
    elif token_exp - now > 60:
        is_valid = True
    
    if sp_token:
        if token_exp - now < 60:
            token_info = oauth.refresh_access_token(refresh_token)
            new_token = token_info['access_token']
            sp_token = new_token
            refresh_token = token_info['refresh_token']
            request.user.profile.save(update_fields=['spotify_token','spotify_refresh'])

    context = {'is_valid': is_valid}
    return render(request, 'dashboard.html', context=context)

# import class to handle playlist creation
from frontpage.playlist_creator import MakePlaylist

# initialize spotify credentials
class AuthURL(APIView):
    def get(self, request):
        oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            cache_handler=CustomCacheHandler(request.user),
            show_dialog=True
        )
        auth_url = oauth.get_authorize_url()
        return Response({'url': auth_url}, status=status.HTTP_200_OK)


def callback(request):
    user = request.user
    oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_handler=CustomCacheHandler(request.user),
        show_dialog=True
    )

    if user.profile.spotify_username != '':
        code = oauth.parse_response_code(request.build_absolute_uri())
        token_info = oauth.get_access_token(code)
        user.profile.spotify_token = token_info['access_token']
        user.profile.token_exp = token_info['expires_at']
        user.profile.spotify_refresh = token_info['refresh_token']
        user.profile.save(update_fields=['spotify_token','spotify_refresh','token_exp'])

        return redirect('dashboard')

@login_required(login_url='login')
def make_playlist(request):
    user = request.user
    bc_username = user.profile.bandcamp_username
    sp_username = user.profile.spotify_username
    sp_token = user.profile.spotify_token
    token_exp = user.profile.token_exp
    refresh_token = user.profile.spotify_refresh
    pl_name = user.profile.sp_playlist_name

    oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_handler=CustomCacheHandler(request.user),
        show_dialog=True
    )

    #check if spotify auth token is exprired
    now = int(time.time())
    if sp_token != '' or token_exp - now < 60:
        token_info = oauth.refresh_access_token(refresh_token)
        token = token_info['access_token']
        sp = spotipy.Spotify(auth=token)
    else:
        sp = spotipy.Spotify(auth=sp_token)

    playlist_maker = MakePlaylist(bc_username, sp_username, sp)
    bc_releases = playlist_maker.get_bc_artists()
    album_list = playlist_maker.search_spotify(bc_releases)
    playlist_id = playlist_maker.get_playlist_id(pl_name)
    playlist_maker.create_playlist(album_list, playlist_id)

    messages.success(request, 'Playlist created/updated')

    return redirect('dashboard')

@login_required(login_url='login')
def buy_music(request):
    user = request.user
    sp_token = user.profile.spotify_token
    token_exp = user.profile.token_exp
    refresh_token = user.profile.spotify_refresh

    oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_handler=CustomCacheHandler(request.user),
        show_dialog=True
    )
    
    #check if spotify auth token is exprired
    now = int(time.time())
    if sp_token != '' or token_exp - now < 60:
        token_info = oauth.refresh_access_token(refresh_token)
        token = token_info['access_token']
        sp = spotipy.Spotify(auth=token)
    else:
        sp = spotipy.Spotify(auth=sp_token)

    #get the first 5 user playlists
    user_playlists = [x['name'].lower() for x in sp.current_user_playlists()['items']]
    user_playlists = user_playlists[:5]

    #get playlist ids
    playlist_ids = []
    for playlist in user_playlists:
        playlist_ids.append(sp.current_user_playlists()['items'][user_playlists.index(playlist)]['id'])

    #get the list of artists
    artist_list = []
    for id_ in playlist_ids:
        pl = sp.playlist(id_)
        artists = [x['track']['artists'][0]['name'] for x in pl['tracks']['items']]
        artist_list.extend(artists)
    artist_list = set(artist_list)

    #search the mongodb collection for artists
    bandcamp_info = []
    for artist in artist_list:
        doc = coll.find_one({'artist_name':artist.lower()})

        if doc:
            bandcamp_info.append(doc)
        else:
            continue

    context = {'bc_info': bandcamp_info}
    return render(request, 'buy_music.html', context)

import geojson
from geojson import FeatureCollection, Point, Feature

# import class to create geojson
from frontpage.map_maker import MapMaker
from django.contrib.auth.mixins import LoginRequiredMixin

class MapView(LoginRequiredMixin, View):
    mapbox_token = os.environ['MAPBOX_TOKEN']
    login_url = 'login'
    redirect_field_name = 'redirect_to'
    template_name = 'map.html'
    
    def get(self, request, *args, **kwargs):
        lat = request.user.profile.latitude
        lon = request.user.profile.longitude
        location = request.user.profile.location
        if ',' in location:
            location = location.split(',')[1]
        local_artists = coll.find({'latitude':{'$exists':True},'location':{'$regex':f'({location})'}})
        user_map = MapMaker(local_artists)
        points = user_map.point_properties()
        context = {
            'center': {'center': [lon,lat]},
            'geo': user_map.make_geo_json(points),
            'mapbox_token': {'token': self.mapbox_token}
        }

        return render(request, self.template_name, context)