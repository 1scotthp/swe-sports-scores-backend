from curses.ascii import NUL
from dataclasses import dataclass
from sqlite3 import Date
from jinja2 import Undefined
import requests
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import firestore
from datetime import timedelta

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

    process_data(response.text, sport)
    # writing to a file, should be writing to firebase?
    # with open('json_data.json', 'w') as outfile:
    #     json.dump(response.text, outfile)


def process_data(d, sport):
    #
    # with open('json_data.json') as json_file:
    #     data = json.loads(json.load(json_file))["data"]
    data = json.loads(d)["data"]

    game_array = {}
    i = 0
    for game in data:
        # print(game)

        if game['status'] == 'finished':
            g = Game(home_team=game['home_team']['name'], away_team=game['away_team']['name'],
                     home_score=game['home_score']['current'], away_score=game['away_score']['current'], date=game['start_at'])
            game_array[i] = dataclasses.asdict(g)
        i += 1

    ref = db.reference('results/' + sport + "/")
    ref.set(game_array)


## FOR RETURN VALUES
## first boolean is true if bet was graded
## second boolean is true if bet was correct
def grade_one_bet(results, bet):
    # print("BET", bet, type(bet))
    # print("RESULTS", type(results))

    for game in results: 
        # print("GAME", results)
        # print(json.loads(game), type(json.loads(game)))
        if bet['winTeam'] == game['home_team'] and bet['loseTeam'] == game['away_team']:
            if game['home_score'] > game['away_score']:  # correct
                return True, True

            else:  # incorrect
                return True, False
        elif bet['winTeam'] == game['away_team'] and bet['loseTeam'] == game['home_team']:
            if game['home_score'] < game['away_score']:  # correct
                return True, True
            else:  # incorrect
                return True, False
        else: 
            return False, False

                   


def grade_bets(sport):

    ref = db.reference('results/' + sport + "/")
    results = ref.get()

    db_firestore = firestore.client()
    docs = db_firestore.collection(u'users').stream()
    i = 0
    for doc in docs:
        user = doc.to_dict()
        open_bets = user["open_bets"]  # get all bets for a user
        streak = user["streak"] if "streak" in user.keys() else 0
        i+=1

        still_open_bets = []
        new_graded_bets = []
        new_wins = 0
        new_losses = 0
        for bet in open_bets:  # check to see if the game happened
            graded = False
            if results is not None:
    go over all result games for every game we are grading
                for game in results:
                    if bet['win'] == game['home_team'] and bet['lose'] == game['away_team']:
                        if game['home_score'] > game['away_score']:  # correct
                            new_wins += 1
                            streak = calculate_streak(streak, 1)

                        else:  # incorrect
                            new_losses += 1
                            streak = calculate_streak(streak, -1)

                        graded = True
                        break
                    elif bet['win'] == game['away_team'] and bet['lose'] == game['home_team']:
                        if game['home_score'] < game['away_score']:  # correct
                            new_wins += 1
                            streak = calculate_streak(streak, 1)

                        else:  # incorrect
                            new_losses += 1
                            streak = calculate_streak(streak, -1)

                        graded = True
                        break

                if not graded:
                    still_open_bets.append(bet)
                else:
                    new_graded_bets.append(bet)

        userRef = db_firestore.collection(u'users').document(doc.id)

        if new_wins > -1 or new_losses > 0:
            newUser = {
                "open_bets": still_open_bets,
                "graded_bets": user["graded_bets"] + new_graded_bets,
                "losses": user["losses"] + new_losses,
                "wins": user["wins"] + new_wins,
                "username": user['username'],
                "phoneNumber": user['phoneNumber'],
                "group_chats": user["group_chats"],
                "streak": streak
            }
            userRef.set(
                newUser
            )

    # this could already be in a designated place yeah thats actually way bete
    ref = db.reference('chats/public/')
    allChats = ref.get()

    graded_bets = []
    still_active_bets = []

    for chat in allChats:
        for data in allChats[chat]:
            if data == "picks":
                if "active" in allChats[chat][data] and results != None:
                    for bet in allChats[chat][data]["active"]:
                        print(grade_one_bet(bet=allChats[chat][data]["active"][bet], results=results))
                        # based on return values update the active/completed bets in a group chat

                        #
                    # go through the active picks and maybe move them over

                    # if results[chat] != None:
                    #     for message in results[chat]["picks"]["active"]:
                    #         print(message, results[chat]["picks"]["active"][message])


cred = credentials.Certificate(
    "swe-sports-firebase-firebase-adminsdk-9lnlp-54450378e3.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://swe-sports-firebase-default-rtdb.firebaseio.com/'
})


def load_all():
    sport_arr = ["basketball_nba", "icehockey_nhl"]
    for s in sport_arr:
        load_data(s)
        # process_data(s)


def grade_all():
    sport_arr = ["basketball_nba", "icehockey_nhl", "basketball_ncaab"]
    for s in sport_arr:
        grade_bets(s)


def calculate_streak(streak, operation):
    """
    Params:
        streak: current user's streak
        operation: 1 if bet hits, -1 if bet doesn't hit

    If streak is positive and bet hits it will increment streak
    If streak is negative and bet hits it will assign it 1
    If streak is positive and bet misses it will assign it -1
    If streak is negative and bet misses it will decrement streak
    """
    return operation if (streak * operation) < 0 else (streak + operation)


def main(event, context):
    # load_all()
    grade_all()


if __name__ == '__main__':
    main(1, 1)
