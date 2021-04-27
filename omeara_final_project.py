######################################################
## program: SI 507 Final Project		            ##
## programmer: Maia O'Meara		                    ##
## umid: maiao				                        ##
## date: April 2021			                        ##
'''
Purpose:
This program aims to request user input of a date (anytime after August 4, 1958,
when bilboard started releasing Hot 100 charts), then scrape artist, track, and
ranking data for that week from the Hot 100 chart.

For each list, the program then calls data from the spotify API to summarize the
top 100 for acousticness, dancability, energy, loudness, and valence. These five
values are then compared to the current day's Hot 100 chart and will be printed
to demonstrate whether the Hot 100 list is more or less of each characteristic.

Finally, it prints the top 10 tracks in order for the given date and allows a user
to enter a number to pull up the artist's spotify page for more information.

Data are cached in a json file, with summary data and track info saved in a SQLite
database.

Goal to use the Flask app to display results and request user input in HTML, but tbd on that.
'''
## references:  Code influenced by/borrowed from github
##              users ZiqiLii and plamare/spotipy
######################################################

import json
import requests
import webbrowser
import sqlite3
import flask
from bs4 import BeautifulSoup
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import secrets

client_id = secrets.SPOTIPY_CLIENT_ID
client_secret = secrets.SPOTIPY_CLIENT_SECRET

client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager)

# create a month dict to use for date validation
month_dict = {
    'january': '01',
    'february': '02',
    'march': '03',
    'april': '04',
    'may': '05',
    'june': '06',
    'july': '07',
    'august': '08',
    'september': '09',
    'october': '10',
    'november': '11',
    'december': '12'
}

########################
## Setting up Caching ##
########################

def open_cache():
    ''' opens the cache file if it exists and loads the JSON into
    a dictionary, which it then returns.
    if the cache file doesn't exist, creates a new cache dictionary
    Parameters
    ----------
    None
    Returns
    -------
    The opened cache
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict

def save_cache(cache_dict):
    ''' saves the current state of the cache to disk
    Parameters
    ----------
    cache_dict: dict
        The dictionary to save
    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME,"w")
    fw.write(dumped_json_cache)
    fw.close()

# CACHE_FILENAME = "spotify_cache.json"

# SPOTIFY_CACHE = open_cache()

CACHE_FILENAME = "billboard_cache.json"

BILLBOARD_CACHE = open_cache()

#######################################
## Setting up SQL Database Structure ##
#######################################

conn = sqlite3.connect('Spotify_Database.sqlite')

cur = conn.cursor()

drop_songs = '''
    DROP TABLE IF EXISTS "Songs";
'''

create_songs = '''
    CREATE TABLE IF NOT EXISTS "Songs" (
        "Id"    INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
        "TrackTitle"    TEXT NOT NULL,
        "Artist"    TEXT NOT NULL,
        "Album"    TEXT NOT NULL,
        "Acoustic"    FLOAT NOT NULL,
        "Dance"    FLOAT NOT NULL,
        "Energy"    FLOAT NOT NULL,
        "Loud"    FLOAT NOT NULL,
        "Valence"    FLOAT NOT NULL
    );
'''

cur.execute(drop_songs)
cur.execute(create_songs)

drop_billboard = '''
    DROP TABLE IF EXISTS "Billboard";
'''

create_billboard = '''
    CREATE TABLE IF NOT EXISTS "Billboard" (
        "Id"        INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
        "Date" TEXT NOT NULL,
        "AcousticAvg"    FLOAT NOT NULL,
        "DanceAvg"    FLOAT NOT NULL,
        "EnergyAvg"    FLOAT NOT NULL,
        "LoudAvg"    FLOAT NOT NULL,
        "ValanceAvg"    INTEGER NOT NULL,
        "TopSongID1"    INTEGER NOT NULL,
        "TopSongID2"    INTEGER NOT NULL,
        "TopSongID3"    INTEGER NOT NULL,
        "TopSongID4"    INTEGER NOT NULL,
        "TopSongID5"    INTEGER NOT NULL,
        "TopSongID6"    INTEGER NOT NULL,
        "TopSongID7"    INTEGER NOT NULL,
        "TopSongID8"    INTEGER NOT NULL,
        "TopSongID9"    INTEGER NOT NULL,
        "TopSongID10"   INTEGER NOT NULL
    );
'''

cur.execute(drop_billboard)
cur.execute(create_billboard)

conn.commit()

#######################################################################
## Setting up Song Class that Structures Data for Export and Display ##
#######################################################################

class Song:
    '''a song based on Spotify data, formatted to be inserted into a SQL database

    Instance Attributes
    -------------------
    title: string
        the name of the song

    artist: string
        The artist(s) who performed the track. Each artist object includes a link
        in href to more detailed information about the artist.

    album: string
        The album on which the track appears.
        The album object includes a link in href to full information about the album.

    acoustic: float
        A confidence measure from 0.0 to 1.0 of whether the track is acoustic.
        1.0 represents high confidence the track is acoustic.

    dancability: float
        Danceability describes how suitable a track is for dancing based on a
        combination of musical elements including tempo, rhythm stability,
        beat strength, and overall regularity.
        A value of 0.0 is least danceable and 1.0 is most danceable.

    energy: float
        Energy is a measure from 0.0 to 1.0 and represents a perceptual measure
        of intensity and activity. Typically, energetic tracks feel fast, loud,
        and noisy. For example, death metal has high energy, while a Bach prelude
        scores low on the scale. Perceptual features contributing to this attribute
        include dynamic range, perceived loudness, timbre, onset rate, and general entropy.

    loudness: float
        The overall loudness of a track in decibels (dB). Loudness values are
        averaged across the entire track and are useful for comparing relative
        loudness of tracks. Loudness is the quality of a sound that is the primary
        psychological correlate of physical strength (amplitude).
        Values typical range between -60 and 0 db.

    valence: float
        A measure from 0.0 to 1.0 describing the musical positiveness conveyed
        by a track. Tracks with high valence sound more positive
        (e.g. happy, cheerful, euphoric), while tracks with low valence sound more
        negative (e.g. sad, depressed, angry).
    '''
    def __init__(self, title, artist, album, acousticness=None, dancability=None, energy=None, loudness=None, valence=None):
        self.title = title
        self.artist = artist
        self.album = album
        self.acousticness = acousticness
        self.dancability = dancability
        self.energy = energy
        self.loudness = loudness
        self.valence = valence

    def info(self):
        return self.title + ' by ' + self.artist + ' from the album ' + self.album

    def export(self):
        # query = '''
        # SELECT Id, OrderDate, ShipName
        # FROM [Order]
        # WHERE OrderDate < '2012-07-11'
        # '''
        # result = cursor.execute(query).fetchall()
        pass


#########################################
## Scraping Billboard for Top 100 Info ##
#########################################

def get_current_hot100():
    ''' Creates a list of the top 10 songs for the current week based on the billboard hot 100
    https://www.billboard.com/charts/hot-100/

    Though caching will be used for other calls, this function scrapes without caching because
    the referenced URL updates depending on the time point when a request is made.

    Parameters
    ----------
    None

    Returns
    -------
    list of dictionaries
        Dictionaries include keys for the song rank on the chart, title, and artist, e.g.
        {
        'rank': '1',
        'title': 'Shape of You',
        'artist': 'Ed Sheeran'
    }
    '''
    url = 'https://www.billboard.com/charts/hot-100'
    current_chart = []
    response = requests.get(url)
    billboard_html = response.text
    soup = BeautifulSoup(billboard_html, 'html.parser')
    song_names = soup.find_all('span',class_="chart-element__information__song text--truncate color--primary")
    artist_names = soup.find_all('span',class_="chart-element__information__artist text--truncate color--secondary")

    rank = 1
    for i in range(100):
        song_dict = {
            'rank': rank,
            'title': song_names[i].text.strip(),
            'artist': artist_names[i].text.strip()
        }
        current_chart.append(song_dict)
        rank += 1

    return current_chart

def validate_date(date):
    ''' Checks whether a date is in the proper format for making a billboard request

    Parameters
    ----------
    date: str
        A date in the format MMMMM DD, YYYY

    Returns
    -------
    valid: int
        a date formatted YYYY-MM-DD, if valid date
        0 if invalid date
    '''
    valid = 0
    date_valid = date.split(' ')
    if len(date_valid[2])==4 and date_valid[2].isnumeric():
        day = date_valid[1][:-1]
        if day.isnumeric() and int(day)<32:
            if len(day)==1:
                day = '0' + day
            if date_valid[0].lower() in month_dict.keys():
                valid = date_valid[2]+'-'+month_dict[date_valid[0].lower()]+'-'+day
    return valid

def get_prev_hot100(date):
    ''' Creates a list of the top 10 songs for the specified date based on the billboard hot 100
    https://www.billboard.com/charts/hot-100/

    Caching is used to check whether the date has been previously requested/stored, otherwise the
    data are pulled from the relevant URL

    Parameters
    ----------
    date: str
        A date in the format YYYY-MM-DD

    Returns
    -------
    list of dictionaries
        Dictionaries include keys for the song rank on the chart, title, and artist, e.g.
            {
        'rank': '1',
        'title': 'Shape of You',
        'artist': 'Ed Sheeran'
        }
    '''
    baseurl = 'https://www.billboard.com/charts/hot-100'
    if date in BILLBOARD_CACHE.keys():
        print('using cache')
        return BILLBOARD_CACHE[date]
    else:
        print('scraping data')
        hot100_chart = {
            'date': date,
            'songs': []
        }
        response = requests.get(baseurl+'/'+date)
        billboard_html = response.text
        soup = BeautifulSoup(billboard_html, 'html.parser')
        song_names = soup.find_all('span', class_="chart-element__information__song text--truncate color--primary")
        artist_names = soup.find_all('span', class_="chart-element__information__artist text--truncate color--secondary")

        rank = 1
        for i in range(100):
            song_dict = {
                'rank': rank,
                'title': song_names[i].text,
                'artist': artist_names[i].text
            }
            hot100_chart['songs'].append(song_dict)
            rank += 1
        BILLBOARD_CACHE[date] = hot100_chart
        save_cache(BILLBOARD_CACHE)
        return BILLBOARD_CACHE[date]

baseurl = 'https://api.spotify.com'

##################
## Testing Code ##
##################

# hot100 = get_current_hot100()
# print(hot100) # always shocked when this works :O

date = 'June 2, 2001'
print(validate_date(date))
hot100_prev = get_prev_hot100(validate_date(date))
print(hot100_prev)
hot100_prev = get_prev_hot100(validate_date(date))
print(hot100_prev['songs'][1])

# hot100_april13 = get_prev_hot100(date)
# print(hot100_april13)

if __name__ == "__main__":
    pass
    # current_hot100 = get_current_hot100()
