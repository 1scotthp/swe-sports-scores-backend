
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
import random

import dataclasses


leagueDict = {
    "basketball_nba": 7422,
    "football_nfl": 0,
    "football_ncaa": 0,
    "basketball_ncaab": 7423,
    "icehockey_nhl": 7588,
}

pageDict = {
    "basketball_nba": 35
}


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


@dataclass
class Game:
    home_team: str
    home_score: str
    away_team: str
    away_score: str
    date: Date


def load_data(sport: str):

    url = "https://sportscore1.p.rapidapi.com/events/search"

    tomorrow = Date.today() + timedelta(days=1)
    yesterday = Date.today() - timedelta(days=1)

    querystring = {"date_end": tomorrow, "date_start": yesterday, "status": "finished",
                   "league_id": leagueDict[sport]}

    headers = {
        'x-rapidapi-host': "sportscore1.p.rapidapi.com",
        'x-rapidapi-key': "d7a0b04800msh58ff2b73ec75beep16578djsn56b3afca8958"
    }

    response = requests.request(
        "POST", url, headers=headers, params=querystring)

    with open('json_data.json', 'w') as outfile:
        json.dump(response.text, outfile)


def process_data(sport):
    with open('json_data.json') as json_file:
        data = json.loads(json.load(json_file))["data"]

    game_array = {}
    i = 0

    for game in data:

        if game['status'] == 'finished':
            g = Game(home_team=game['home_team']['name'], away_team=game['away_team']['name'],
                     home_score=game['home_score']['current'], away_score=game['away_score']['current'], date=game['start_at'])
            game_array[i] = dataclasses.asdict(g)
        i += 1

    ref = db.reference('results/' + sport + "/")
    ref.set(game_array)


def grade_bets(sport):

    ref = db.reference('results/' + sport + "/")
    results = ref.get()

    db_firestore = firestore.client()
    docs = db_firestore.collection(u'users').stream()
    i = 0
    for doc in docs:
       
        open_bets = doc.to_dict()["open_bets"]  # get all bets for a user
        print(i, open_bets)
        i+=1
        still_open_bets = []
        new_graded_bets = []
        new_wins = 0
        new_losses = 0
        for bet in open_bets:  # check to see if the game happened
            graded = False
            for game in results:
                if bet['win'] == game['home_team'] and bet['lose'] == game['away_team']:
                    if game['home_score'] > game['away_score']:  # correct
                        new_wins += 1
                    else:  # incorrect
                        new_losses += 1
                    graded = True
                    break
                elif bet['win'] == game['away_team'] and bet['lose'] == game['home_team']:
                    if game['home_score'] < game['away_score']:  # correct
                        new_wins += 1
                    else:  # incorrect
                        new_losses += 1
                    graded = True
                    break
                
            if not graded:
                still_open_bets.append(bet)
            else: 
                new_graded_bets.append(bet)


        userRef = db_firestore.collection(u'users').document(doc.id)

        if new_wins > -1 or new_losses > 0:
            user = doc.to_dict()
            newUser = {
                "open_bets": still_open_bets,
                "graded_bets": user["graded_bets"]+new_graded_bets,
                "losses": user["losses"] + new_losses,
                "wins": user["wins"] + new_wins,
                "username": user['username'],
                "phoneNumber": user['phoneNumber'],
                "group_chats": user["group_chats"]
            }
            print(i, newUser["open_bets"])
            userRef.set(
                newUser
            )


cred = credentials.Certificate(
    "swe-sports-firebase-firebase-adminsdk-9lnlp-54450378e3.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://swe-sports-firebase-default-rtdb.firebaseio.com/'
})


def load_all():
    sport_arr = ["basketball_nba", "icehockey_nhl", "basketball_ncaab"]
    for s in sport_arr:
        load_data(s)
        process_data(s)


def grade_all():
    sport_arr = ["basketball_nba", "icehockey_nhl", "basketball_ncaab"]
    for s in sport_arr:
        grade_bets(s)


load_all()
grade_all()
