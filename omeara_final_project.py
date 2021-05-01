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
top 10 for acousticness, danceability, energy, loudness, and valence. It prints
the songs in order, then provides a comparison list of these five values versus
the current day's Hot 100 chart. These are displayed below the list
to demonstrate whether the Hot 100 list is more or less of each characteristic.

It then asks if the user would like to see a radar chart of the data, in which case
they can enter "yes" to pull up a chart in their browser.

Finally, it prints the top 10 tracks in order for the given date and allows a user
to enter a number to pull up the full Billboard list for more information.

Data are cached in a json file, with summary data and track info saved in a SQLite
database.
'''
## references:  Code influenced by/borrowed from github
##              users ZiqiLii and plamare/spotipy
######################################################

import json
import requests
import webbrowser
import sqlite3
from bs4 import BeautifulSoup
import plotly.express as px
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import secrets

cid = secrets.SPOTIPY_CLIENT_ID
c_secret = secrets.SPOTIPY_CLIENT_SECRET

client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=c_secret)
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

CACHE_FILENAME = "billboard_cache.json"

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

    acousticness: float
        A confidence measure from 0.0 to 1.0 of whether the track is acoustic.
        1.0 represents high confidence the track is acoustic.

    danceability: float
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
    def __init__(self, song_id, title, artist, album, acousticness=None, danceability=None, energy=None, loudness=None, valence=None):
        self.id = song_id
        self.title = title
        self.artist = artist
        self.album = album
        self.acousticness = acousticness
        self.danceability = danceability
        self.energy = energy
        self.loudness = loudness
        self.valence = valence

    def info(self):
        return self.title + ' by ' + self.artist + ' from "' + self.album + '"'

    def export(self, dbtable):
        '''
        Checks whether a song is in the database already and, if not, adds it
        '''
        query = f'''
        SELECT COUNT(DISTINCT TrackTitle)
        FROM [Songs]
        WHERE TrackTitle = "{self.title}" AND Artist = "{self.artist}"
        '''
        result = cur.execute(query).fetchall()
        if result[0][0] == 0:
            insert_song = f'''
                INSERT INTO "Songs" 
                ("TrackTitle", "Artist", "Album", "Acoustic", "Dance", "Energy", "Loud", "Valence") 
                VALUES ("{self.title}", "{self.artist}", "{self.album}", "{self.acousticness}", 
                "{self.danceability}", "{self.energy}", "{self.loudness}", "{self.valence}"
                );
            '''
            cur.execute(insert_song)
        conn.commit()


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
    for i in range(10):
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
    try:
        date_valid = date.split(' ')
        if len(date_valid[2])==4 and date_valid[2].isnumeric():
            day = date_valid[1][:-1]
            if day.isnumeric() and int(day)<32:
                if len(day)==1:
                    day = '0' + day
                if date_valid[0].lower() in month_dict.keys():
                    valid = date_valid[2]+'-'+month_dict[date_valid[0].lower()]+'-'+day
        return valid
    except:
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
        for i in range(10):
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

######################################
## Fetching Data from Spotify's API ##
######################################

def create_query(title, artist):
    ''' Takes a title and artist from Billboard and processes it as a meaningful spotify search query.

    Keyword should only be the title and artist, limit to 10 observations
    Split the artist name at a comma, if there is one, or at "Featuring" if that
    phrase is included in the artist
    Also cut out any text between quotation marks, if that exists (specifically ")
    Parameters
    ----------
    title: str
        The title of a track
    artist: str
        The artist(s) that produced the track

    Returns
    -------
    query: str
        The search query for spotify
    '''
    query = None
    artist_rev = artist.lower()
    title_rev = title.lower()
    if "featuring" in artist_rev:
        art_list = artist_rev.split(' featuring')
        artist_rev = art_list[0]
    if "," in artist:
        art_list = artist_rev.split(',')
        artist_rev = art_list[0]
    if '"' in artist:
        art_list = artist_rev.split('"')
        artist_rev = art_list[0]
    if '"' in title:
        title_list = title_rev.split('"')
        title_rev = title_list[0]
    if '/' in title:
        title_list = title_rev.split('/')
        title_rev = title_list[0]

    query = title_rev + " " + artist_rev
    return query

def spotify_search(query):
    ''' Searches spotify for tracks based on specified keywords, processed in the create_query function.

    Need to pull the Spotify IDs for the top song result with the EXACT name (and check that popularity is >20?),
    then use those in a audio features query.

    Information is returned as a Song class object

    Parameters
    ----------
    keywords: str
        The search query for spotify

    Returns
    -------
    spotify_song: Song
        A Song class object with required attributes specified
    '''

    if query in BILLBOARD_CACHE.keys():
        print('using cache')
    else:
        print('scraping data')
        BILLBOARD_CACHE[query] = sp.search(q=query)
        save_cache(BILLBOARD_CACHE)
    raw_results = BILLBOARD_CACHE[query]
    song_id = raw_results['tracks']['items'][0]['id']
    title = raw_results['tracks']['items'][0]['name']
    artist = raw_results['tracks']['items'][0]['artists'][0]['name']
    album = raw_results['tracks']['items'][0]['album']['name']
    spotify_song = Song(song_id, title, artist, album)
    return spotify_song

def get_song_attributes(song_list):
    ''' Takes Song class objects and updates to include audio attributes from Spotify
    Upon creating a full Song object, exports that song to a database.

    Parameters
    ----------
    song_list: list of song objects
        The search query for spotify

    Returns
    -------
    song_list: list of song objects
        An updated list of Song class object with all audio features specified
    '''
    id_list = []
    for song in song_list:
        id_list.append(song.id)
    features = sp.audio_features(id_list)
    for i in range(len(song_list)):
        song_list[i].acousticness = features[i]['acousticness']
        song_list[i].danceability = features[i]['danceability']
        song_list[i].energy = features[i]['energy']
        song_list[i].loudness = features[i]['loudness']
        song_list[i].valence = features[i]['valence']
        song_list[i].export('Songs')
    return song_list


##############################################
## Creating Average Scores for Top 10 Songs ##
##############################################

def average_attributes(song_list):
    ''' Takes a list of Song class objects and calculates their average attributes

    Parameters
    ----------
    song_list: list of song objects

    Returns
    -------
    avg_attributes: a dictionary
        summary
    '''
    avg_attributes = {
        'acousticness': float(0.0),
        'danceability': float(0.0),
        'energy': float(0.0),
        'loudness': float(0.0),
        'valence': float(0.0)
    }
    for song in song_list:
        avg_attributes['acousticness'] += float(song.acousticness)
        avg_attributes['danceability'] += float(song.danceability)
        avg_attributes['energy'] += float(song.energy)
        avg_attributes['loudness'] += float(song.loudness)
        avg_attributes['valence'] += float(song.valence)
    for key, val in avg_attributes.items():
        avg_attributes[key] = round(val/float(len(song_list)), ndigits=3)
    return avg_attributes

def compare_attributes(attributes_1, attributes_2):
    ''' Takes two dictionaries of attributes and compares their acousticness, danceability,
    energy, loudness, and valence.

    The second attribute dictionary is subtracted from the first. For all but loudness, a
    negative value means that the second dictionary is more of the characteristic than the first.
    For loudness, which is measured in decibles a positive value implies that the second value is
    louder than the first and a negative value implies that is is quieter.

    Parameters
    ----------
    attributes_1 and 2: dictionaries of attributes

    Returns
    -------
    comp_attributes: a dictionary
        summary of the differences in attributes
    '''
    comp_attributes = {
        'attributes_1': attributes_1,
        'attributes_2': attributes_2,
        'acousticness': attributes_1['acousticness'] - attributes_2['acousticness'],
        'danceability': attributes_1['danceability'] - attributes_2['danceability'],
        'energy': attributes_1['energy'] - attributes_2['energy'],
        'loudness': attributes_1['loudness'] - attributes_2['loudness'],
        'valence': attributes_1['valence'] - attributes_2['valence']
    }
    return comp_attributes

def plot_song_attributes(attributes):
    '''Takes two dictionaries of attributes and compares their acousticness, danceability,
    energy, loudness, and valence.

    The second attribute dictionary is subtracted from the first. For all but loudness, a
    negative value means that the second dictionary is more of the characteristic than the first.
    For loudness, which is measured in decibles a positive value implies that the second value is
    louder than the first and a negative value implies that is is quieter.

    Parameters
    ----------
    attributes: dictionaries of song attributes

    Returns
    -------
    attributes_plot: a radar plot of song attributes
    '''
    song_data = pd.DataFrame(dict(
            attr_values=[attributes['acousticness'], attributes['danceability'], attributes['energy'], attributes['valence']],
            attr_labels=['Acousticness','Danceability','Energy', 'Valence']))
    song_fig = px.line_polar(song_data, r='attr_values', theta='attr_labels', line_close=True)
    # song_fig.write_html("attributes.html", auto_open=True)
    song_fig.show()


if __name__ == "__main__":
    # Accessing comparison data:

    current_hot100 = get_current_hot100()
    current_song_list = []
    for song in current_hot100:
        song_query = create_query(song['title'], song['artist'])
        song_data = spotify_search(song_query)
        current_song_list.append(song_data)
    current_song_list_full = get_song_attributes(current_song_list)
    current_song_attributes = average_attributes(current_song_list_full)

    # Starting program
    print('-------------------------------------')
    print('Welcome to the Spotify Time Capsule!')
    print('-------------------------------------')
    date_input = input("Please enter a date in the format Month DD, YYYY: ")

    while True:
        if date_input.lower() == 'exit':
            print('Bye!')
            quit()
        elif validate_date(date_input)==0:
            print("I'm sorry, that date is invalid.")
            date_input = input("Please enter a date in the format 'Month DD, YYYY' or 'Exit' to end the program: ")
        else:
            prev_hot100 = get_prev_hot100(validate_date(date_input))
            song_list = []
            for song in prev_hot100['songs']:
                prev_query = create_query(song['title'], song['artist'])
                try:
                    prev_song_data = spotify_search(prev_query)
                    song_list.append(prev_song_data)
                except:
                    continue
            song_list_full = get_song_attributes(song_list)
            print(' ')
            print(f'Here are the top 10 songs from the Billboard Hot 100 list for {date_input}!')
            print('-----------------------------------------------------------------------------')
            for song in song_list_full:
                print('[' + str(song_list_full.index(song)+1) + '] ' + song.info())
            print('-----------------------------------------------------------------------------')
            prev_song_attributes = average_attributes(song_list_full)
            comp_results = compare_attributes(current_song_attributes, prev_song_attributes)
            print(' ')
            print(f'Compared to the current Hot 100 list, songs from {date_input} are:')
            if comp_results['acousticness'] > 0:
                print(f"* LESS acoustic (average acousticness score = {prev_song_attributes['acousticness']})")
            elif comp_results['acousticness'] < 0:
                print(f"* MORE acoustic (average acousticness score = {prev_song_attributes['acousticness']})")
            elif comp_results['acousticness'] == 0:
                print(f"* EQUALLY acoustic (average acousticness score = {prev_song_attributes['acousticness']})")
            if comp_results['danceability'] > 0:
                print(f"* LESS danceable (average danceability score = {prev_song_attributes['danceability']})")
            elif comp_results['danceability'] < 0:
                print(f"* MORE danceable (average danceability score = {prev_song_attributes['danceability']})")
            elif comp_results['danceability'] == 0:
                print(f"* EQUALLY danceable (average danceability score = {prev_song_attributes['danceability']})")
            if comp_results['energy'] > 0:
                print(f"* LESS energetic (average energy score = {prev_song_attributes['energy']})")
            elif comp_results['energy'] < 0:
                print(f"* MORE energetic (average energy score = {prev_song_attributes['energy']})")
            elif comp_results['energy'] == 0:
                print(f"* EQUALLY energetic (average energy score = {prev_song_attributes['energy']})")
            if comp_results['loudness'] < 0:
                print(f"* LESS loud (average volume in decibels = {prev_song_attributes['loudness']})")
            elif comp_results['loudness'] > 0:
                print(f"* MORE loud (average volume in decibels = {prev_song_attributes['loudness']})")
            elif comp_results['loudness'] == 0:
                print(f"* EQUALLY loud (average volume in decibels = {prev_song_attributes['loudness']})")
            if comp_results['valence'] > 0:
                print(f"* LESS happy (average valence score = {prev_song_attributes['valence']})")
            elif comp_results['valence'] < 0:
                print(f"* MORE happy (average valence score = {prev_song_attributes['valence']})")
            elif comp_results['valence'] == 0:
                print(f"* EQUALLY happy (average valence score = {prev_song_attributes['valence']})")
            print(' ')
            plot_request = input("Would you like to see a plot of these attributes? [Enter 'yes' or 'no'] ")
            if plot_request.lower() == 'yes':
                plot_song_attributes(prev_song_attributes)
            print('-----------------------------------------------------------------------------')
            print(' ')
            while True:
                item_num = input("Enter a rank number to pull up the full Hot 100 list, another date to search, or 'exit' to end this session: ")
                if item_num.isnumeric():
                    url = 'https://www.billboard.com/charts/hot-100/'+validate_date(date_input)
                    webbrowser.open(url)
                    date_input = input("Please enter a date in the format 'Month DD, YYYY' or 'Exit' to end the program: ")
                    break
                else:
                    date_input = item_num
                    break

'''
TO DO:
Set up Billboard relational database table

Update Read Me file

Make a demo video
'''