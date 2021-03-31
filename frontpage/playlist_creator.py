from bs4 import BeautifulSoup
import requests
import time


''' spotify api only allows 20 albums to be searched at a time.
this function breaks of the album ideas to make multiple requests
if there are more than 20 albums '''

def break_up_albums(album_ids, sp):
    trax = []
    size = len(album_ids)
    if size <= 20:
        for album in list(sp.albums(album_ids)['albums']):
            trax.extend([x['id'] for x in album['tracks']['items']])
        return trax
    else:
        while size > 20:
            case = album_ids[size-20:size]
            for album in list(sp.albums(case)['albums']):
                trax.extend([x['id'] for x in album['tracks']['items']])
            size = size - 20
            time.sleep(1)
        case = album_ids[:size]
        for album in list(sp.albums(case)['albums']):
                trax.extend([x['id'] for x in album['tracks']['items']])
        return trax

class MakePlaylist():
    def __init__(self, bc_username, sp_username, sp):
        self.bc_username = bc_username
        self.sp_username = sp_username
        self.sp = sp
    
    def get_playlist_id(self,pl_name):

        playlists = [x['name'].lower() for x in self.sp.current_user_playlists()['items']]

        #determine playlist ID
        if pl_name.lower() not in playlists:
            self.sp.user_playlist_create(user=self.sp_username, name=pl_name) #create a new playlist
            playlist_id = self.sp.current_user_playlists()['items'][0]['id'] #grab new playlist ID
            return playlist_id

        elif pl_name.lower() in playlists:
            playlist_id = self.sp.current_user_playlists()['items'][playlists.index(pl_name.lower())]['id']
            return playlist_id

    def get_bc_artists(self):
        page = requests.get(f'https://bandcamp.com/{self.bc_username}')
        soup = BeautifulSoup(page.text, 'html.parser')
        artist_collection = soup.find_all('div', class_='collection-item-artist')
        title_collection = soup.find_all('div', class_='collection-item-title')
        artist_list = [artist_collection[x].get_text().split('by ')[1] for x in range(0, len(artist_collection), 2)]
        title_list = [title_collection[x].get_text().split('\n')[0] for x in range(0,len(title_collection), 2)]
        release_list = []
        for artist, title in zip(artist_list, title_list):
            release_list.append({'artist': artist, 'title': title})
        return release_list

    def search_spotify(self, releases):
        album_ids = []

        for release in releases:
            results = self.sp.search(q= f"{release['artist']} {release['title']}", type='album', limit=1)

            if any(results['albums']['items']) and release['artist'].lower() == results['albums']['items'][0]['artists'][0]['name'].lower():
                album_ids.append(results['albums']['items'][0]['id'])
            else:
                continue
            time.sleep(1)
        return break_up_albums(album_ids, self.sp)

    def create_playlist(self, results, playlist_id):
        size = len(results)
        if size <= 100:
            return self.sp.user_playlist_add_tracks(user=self.sp_username, playlist_id= playlist_id, tracks=results)
        else:
            while size > 100:
                case = results[size-100:size]
                self.sp.user_playlist_add_tracks(user=self.sp_username, playlist_id=playlist_id, tracks=case)
                size = size - 100
                time.sleep(3)
            case = results[:size]
            return self.sp.user_playlist_add_tracks(user=self.sp_username, playlist_id=playlist_id, tracks=case)