# si507-finalproject: Spotify Time Capsule
Name: Maia O’Meara
Uniqname: maiao
Course: SI 507.002
Assignment: Final Project Submission

This program request user input of a date, then scrapes artist, track, and ranking data for that week from the Hot 100 chart.

For each list, the program then calls data from the Spotify API to summarize the top 10 for acousticness, danceability, energy, loudness, and valence. It prints the songs in order, then provides a comparison list of these five values versus the current day's Hot 100 chart. These are displayed below the list to demonstrate whether the Hot 100 list is more or less of each characteristic.

It then asks if the user would like to see a radar chart of the data, in which case they can enter "yes" to pull up a chart in their browser.

Finally, it allows a user to enter a ranking number to pull up the full Billboard list for more information.

**Required Programs**
import json
import requests
import webbrowser
import sqlite3
from bs4 import BeautifulSoup
import plotly.express as px
import pandas as pd
import spotipy

In addition, the user needs to create a Spotify Developer Account (instructions here: https://developer.spotify.com/documentation/web-api/quick-start/) and save a secrets.py file with their Spotify Client ID and Spotify Client Secret (both of which are available on your Spotify for Developers Dashboard once you set it up).

Billboard is easily scrapable with no necessary authorization.

**Interaction**
The interactive elements for this project are all controlled through the command line. The program first requests a date and, based on this information, pulls a list of the top 10 songs for that date off of Billboard’s website (display 1). 

Then, the program compares those data to the current top 10 songs and presents a text summary of the differences between those songs and the ones you just pulled with a past date (display 2). 

Next, a user is asked whether they would like to see a plot of the song qualities that make the current list similar or different (display 3). If they enter yes, a radar chart is created and displayed using Plotly.
Finally, the user is asked to enter a rank number to pull up more information from the Billboard Hot 100 list in their web browser (display 4). 

At any point, they can enter a new date to search or “Exit” to quit the program.


