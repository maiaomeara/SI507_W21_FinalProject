##############################################
## program: Final Project		            ##
## programmer: Maia O'Meara		            ##
## umid: maiao				                ##
## date: April 2021			                ##
## purpose: Access the Spotify API	        ##
##
##
##
###############################################

import json
import requests
import webbrowser
import plotly.graph_objects as go
import sqlite3
import flask

conn = sqlite3.connect('Spotify_Database.sqlite')

cur = conn.cursor()

drop_songs = '''
    DROP TABLE IF EXISTS "Songs";
'''

create_songs = '''
    CREATE TABLE IF NOT EXISTS "Songs" (
        "Id"    INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
        "TrackTitle"    TEXT NOT NULL,
        "ArtistID"    INTEGER NOT NULL,
        "Album"    TEXT NOT NULL,
        "PlayCount"    INTEGER NOT NULL
    );
'''

cur.execute(drop_songs)
cur.execute(create_songs)

drop_artists = '''
    DROP TABLE IF EXISTS "Artists";
'''

create_artists = '''
    CREATE TABLE IF NOT EXISTS "Artists" (
        "Id"        INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
        "Artist" TEXT NOT NULL,
        "Country"  TEXT NOT NULL,
        "MonthlyListeners"    INTEGER NOT NULL,
        "TopCountry1"    TEXT,
        "TopCountry2"    TEXT,
        "TopCountry3"    TEXT,
        "TopCountry4"    TEXT,
        "TopCountry5"    TEXT
    );
'''

cur.execute(drop_artists)
cur.execute(create_artists)

conn.commit()