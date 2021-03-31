from django.shortcuts import render, redirect
from django.views import generic
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required

# app imports
from frontpage.models import Map, Profile
from frontpage.forms import CreateUserForm, MapForm, ProfileForm
from frontpage.playlist_creator import MakePlaylist

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
            'sp_playlist_name': user.profile.sp_playlist_name
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
    context = {}
    return render(request, 'dashboard.html', context=context)



''' Spotify auth & user experience '''
# needed for refreshing tokens
import time

# handling spotify auth
from rest_framework.response import Response
from rest_framework import status
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# initialize spotify credentials
oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri='http://localhost:8080/',
    scope=scope
)

@login_required(login_url='login')
def get_auth_url(request):
    user = request.user

    if user.profile.bandcamp_username != '' and user.profile.spotify_username != '':

        auth_url = oauth.get_authorize_url()
        response = Response({'url': auth_url}, status=status.HTTP_200_OK)
        code = oauth.parse_response_code(request.GET.get(response))
        token_info = oauth.get_access_token(code)

        user.profile.spotify_token = token_info['access_token']
        user.profile.token_exp = token_info['expires_at']
        user.profile.spotify_refresh = token_info['refresh_token']
        user.profile.save(update_fields=['spotify_token','spotify_refresh','token_exp'])

        messages.success(request, 'Spotify is authenicated')
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

    now = int(time.time())
    if sp_token != '' or token_exp - now < 60:
        sp = spotipy.Spotify(auth=sp_token)
    else:
        sp = spotipy.Spotify(auth=refresh_token)

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

    now = int(time.time())
    if sp_token != '' or token_exp - now < 60:
        sp = spotipy.Spotify(auth=sp_token)
    else:
        sp = spotipy.Spotify(auth=refresh_token)

    user_playlists = [x['name'].lower() for x in sp.current_user_playlists()['items']]
    user_playlists = user_playlists[:5]

    playlist_ids = []
    for playlist in user_playlists:
        playlist_ids.append(sp.current_user_playlists()['items'][user_playlists.index(playlist)]['id'])

    artist_list = []
    for id_ in playlist_ids:
        pl = sp.playlist(id_)
        artists = [x['track']['artists'][0]['name'] for x in pl['tracks']['items']]
        artist_list.extend(artists)
    artist_list = set(artist_list)

    bandcamp_info = []
    for artist in artist_list:
        doc = coll.find_one({'artist_name':artist.lower()})

        if doc:
            bandcamp_info.append(doc)
        else:
            continue
    context = {'bc_info': bandcamp_info}
    return render(request, 'buy_music.html', context)


@login_required(login_url='login')
def MapView(request):
    user = request.user
    form = MapForm(initial={
        'country_region': user.profile.location
    })
    if request.method == 'POST':
        form = MapForm(request.POST)
        if form.is_valid():
            form.save()
    query = Map.objects.filter(country_region=request.POST.get('country_region')).values('latitude', 'longitude')
    if query:
        center = [list(query)[0]['longitude'],list(query)[0]['latitude']]
        context = {'form': form, 'center': center}
    else:
        context = {'form': form}
    return render(request, 'map.html', context=context)