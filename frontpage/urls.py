from django.urls import path
from .views import *

urlpatterns = [
    path('', landingpage, name='index'),
    path('register/', register, name='register'),
    path('login/', loginPage, name='login'),
    path('profile/', profile, name='profile'),
    path('logout/', logout_user, name='logout'),
    path('get-auth-url/', AuthURL.as_view()),
    path('make-playlist/', make_playlist, name='make-playlist'),
    path('redirect/', callback),
    path('buy_music/', buy_music, name='buy-music'),
    path('dashboard/', dashboard, name='dashboard'),
    path('map/', MapView.as_view(), name='map'),
]

