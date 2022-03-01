import datetime
import requests
import base64
import pickle
from urllib.parse import urlencode
import webbrowser

from ValidatorError import ValidatorError


class SpotifyAPIFlow(object):
    access_token = None
    access_token_expires = datetime.datetime.now()
    access_token_did_expire = True
    client_id = None
    client_secret = None
    token_url = "https://accounts.spotify.com/api/token"
    auth_url = "https://accounts.spotify.com/authorize"
    refresh_token = None
    authentication_code = None

    def __init__(self, client_id, client_secret, filename=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret
        self.filename = filename

    def __get_client_credentials(self):
        """
        :return: a base 64 encoded string
        """
        client_id = self.client_id
        client_secret = self.client_secret
        if client_secret is None or client_id is None:
            raise ValidatorError("You must set client id and client secret!\n")
        client_creds = f"{client_id}:{client_secret}"
        client_creds_b64 = base64.b64encode(client_creds.encode())
        return client_creds_b64.decode()

    def __get_token_headers(self):
        client_creds_b64 = self.__get_client_credentials()
        return {"Authorization": f"Basic {client_creds_b64}"}

    @staticmethod
    def __get_token_data():
        return {"grant_type": "authorization_code"}

    def __perform_authentication(self):
        if self.filename is not None:
            self.__read_codes_from_file()
            if self.access_token is not None:
                return
        auth_url = self.auth_url
        headers = {'client_id': self.client_id, 'response_type': 'code',
                   'redirect_uri': 'http://localhost:8888/callback',
                   'scope': 'user-top-read'}
        auth_code = requests.get(auth_url, headers)
        if auth_code.status_code not in range(200, 299):
            raise ValidatorError("Authentication failed!")
        token_headers = self.__get_token_headers()

        webbrowser.open(f"{auth_url}?client_id={self.client_id}&response_type=code&redirect_uri=http:%2F%2Flocalhost:8888%2Fcallback&scope=user-top-read")
        auth_code = input("Your code is:\n")
        self.authentication_code = auth_code
        payload = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': 'http://localhost:8888/callback'
        }
        access_token_request = requests.post(url=self.token_url, data=payload, headers=token_headers)
        access_token_response_data = access_token_request.json()
        self.access_token = access_token_response_data['access_token']
        self.access_token_expires = datetime.datetime.now() + datetime.timedelta(seconds=access_token_response_data['expires_in'])
        self.refresh_token = access_token_response_data['refresh_token']
        if self.filename:
            self.__write_codes_to_file()

    def __perform_refresh_authentication(self):
        token_headers = self.__get_token_headers()
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
        }
        access_token_request = requests.post(url=self.token_url, data=data, headers=token_headers)
        access_token_response_data = access_token_request.json()
        self.access_token = access_token_response_data['access_token']
        self.access_token_expires = datetime.datetime.now() + datetime.timedelta(
            seconds=access_token_response_data['expires_in'])
        if self.filename:
            self.__write_codes_to_file()

    def __read_codes_from_file(self):
        with open(self.filename, "rb") as file:
            try:
                codes = pickle.load(file)
            except EOFError:
                codes = None
            if isinstance(codes, list) and len(codes) == 4:
                self.authentication_code = codes[0]
                self.access_token = codes[1]
                self.refresh_token = codes[2]
                self.access_token_expires = codes[3]
                self.access_token_did_expire = self.access_token_expires < datetime.datetime.now()

    def __write_codes_to_file(self):
        auth_code = self.authentication_code
        access_token = self.access_token
        refresh_token = self.refresh_token
        access_token_expires = self.access_token_expires
        codes = [auth_code, access_token, refresh_token, access_token_expires]
        with open(self.filename, "wb") as file:
            pickle.dump(codes, file)

    def __get_access_token(self):
        token = self.access_token
        expires = self.access_token_expires
        now = datetime.datetime.now()
        if token is None:
            self.__perform_authentication()
            return self.__get_access_token()
        if expires < now:
            self.__perform_refresh_authentication()
            return self.__get_access_token()
        return token

    def __get_resource_header(self):
        access_token = self.__get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"
                   }
        return headers

    def __get_resource(self, lookup_id, resource_type='albums', version='v1'):
        base_url = "https://api.spotify.com"
        endpoint = f"{base_url}/{version}/{resource_type}/{lookup_id}"
        headers = self.__get_resource_header()
        r = requests.get(endpoint, headers=headers)
        if r.status_code not in range(200, 299):
            return {}
        return r.json()

    def __get_album(self, _id):
        return self.__get_resource(_id, resource_type='albums')

    def __get_artist(self, _id):
        return self.__get_resource(_id, resource_type='artists')

    def __base_search(self, query_params):
        headers = self.__get_resource_header()
        endpoint = "https://api.spotify.com/v1/search"
        lookup_url = f"{endpoint}?{query_params}"
        r = requests.get(lookup_url, headers=headers)
        if r.status_code in range(200, 299):
            return r.json()
        return {}

    def search(self, query=None, operator=None, operator_query=None, search_type='artist'):
        if query is None:
            raise ValidatorError("A query is required")
        if isinstance(query, dict):
            query = " ".join([f"{key}:{value}" for key, value in query.items()])
        if operator is not None and operator_query is not None:
            if operator.lower() == "or" or operator.lower() == "not":
                operator = operator.upper()
                if isinstance(operator_query, str):
                    query = f"{query} {operator} {operator_query}"
        query_params = urlencode({"q": query, "type": search_type.lower()})
        disorganised_info = self.__base_search(query_params)
        options = {"track": self.__get_searched_track, "artist": self.__get_searched_artist, "album": self.__get_searched_album}
        if search_type not in options.keys():
            return {}
        else:
            return options[search_type](disorganised_info)

    def get_personalized_info(self, type='tracks', time_range='medium_term', limit=50, offset=0):
        headers = self.__get_resource_header()
        endpoint = "https://api.spotify.com/v1/me/top/"
        lookup_url = f"{endpoint}{type}?time_range={time_range}&limit={limit}&offset={offset}"
        r = requests.get(lookup_url, headers=headers)
        if r.status_code in range(200, 299):
            rJson = r.json()
            if type == 'tracks':
                return self.__get_top_tracks(rJson)
            elif type == 'artists':
                return self.__get_top_artists(rJson)
            else:
                raise ValidatorError("Invalid Type!\n")
        else:
            return {}

    @staticmethod
    def __decrypt_song(song):
        length_ms = int(song['duration_ms'])
        length_s = length_ms // 1000
        minutes = length_s // 60
        seconds = length_s % 60

        artists_names = []
        for artist in song['artists']:
            artists_names.append(artist['name'])
        song_dict = {"name": song['name'], "artist": artists_names,
                     "album": song['album']['name'],
                     "release date": song['album']['release_date'], "minutes": minutes, "seconds": seconds,
                     "id": song['id']}
        return song_dict

    @staticmethod
    def __decrypt_artist(artist):
        artist_dict = {"name": artist['name'], "genres": artist['genres'],
                       "followers": artist['followers']['total'], "id": artist['id']}
        return artist_dict

    @staticmethod
    def __decrypt_album(album):
        artists_names = []
        for artist in album['artists']:
            artists_names.append(artist['name'])
        album_dict = {"name": album["name"], "artists": artists_names, "type": album["album_type"],
                      "date": album["release_date"], "number of tracks": album["total_tracks"]}
        return album_dict

    @staticmethod
    def __get_top_tracks(disorganized_json_data):
        relevant_values = []
        for pos, song in enumerate(disorganized_json_data['items']):
            song_dict = SpotifyAPIFlow.__decrypt_song(song)
            song_dict["position"] = pos + 1
            relevant_values.append(song_dict)
        return relevant_values

    @staticmethod
    def __get_top_artists(disorganised_json_data):
        relevant_values = []
        for pos, artist in enumerate(disorganised_json_data['items']):
            artist_dict = SpotifyAPIFlow.__decrypt_artist(artist)
            artist_dict["position"] = pos + 1
            relevant_values.append(artist_dict)
        return relevant_values

    @staticmethod
    def __get_searched_track(disorganized_json_data):
        relevant_data = []
        for pos, song in enumerate(disorganized_json_data['tracks']['items']):
            if pos >= 5:
                break
            decrypted_data = SpotifyAPIFlow.__decrypt_song(song)
            decrypted_data["position"] = pos + 1
            relevant_data.append(decrypted_data)
        return relevant_data

    @staticmethod
    def __get_searched_artist(disorganized_json_data):
        relevant_data = []
        for pos, artist in enumerate(disorganized_json_data['artists']['items']):
            if pos >= 2:
                break
            decrypted_data = SpotifyAPIFlow.__decrypt_artist(artist)
            decrypted_data["position"] = pos + 1
            relevant_data.append(decrypted_data)
        return relevant_data

    @staticmethod
    def __get_searched_album(disorganized_json_data):
        relevant_data = []
        for pos, album in enumerate(disorganized_json_data['albums']['items']):
            if pos >= 2:
                break
            decrypted_data = SpotifyAPIFlow.__decrypt_album(album)
            decrypted_data["position"] = pos + 1
            relevant_data.append(decrypted_data)
        return relevant_data

