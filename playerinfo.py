from nba_api.stats.static import players
from dataclasses import dataclass
from sqlite3 import Date
import requests
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import firestore
from datetime import date
from datetime import timedelta



cred = credentials.Certificate(
    "swe-sports-firebase-firebase-adminsdk-9lnlp-54450378e3.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://swe-sports-firebase-default-rtdb.firebaseio.com/'
})








def uploadData():
    ref = db.reference("NBA/playerInfo/")

    ref.set(players.get_active_players())

uploadData()

    





