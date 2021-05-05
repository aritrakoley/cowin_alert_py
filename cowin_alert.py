import requests
import json
import time
import datetime
import os

# USER DEFINED VARIABLES
# STATE = 'Delhi'
# DISTRICT = 'New Delhi'
STATE = 'West Bengal'
DISTRICT = 'Kolkata'
MIN_AGE = 18
WEEKS_TO_CHECK = 3

# SYSTEM DEFINED VARIABLES
START_DATE = datetime.date.today()
END_DATE = START_DATE + datetime.timedelta(days=7)
START_DATE_STR = START_DATE.strftime("%d-%m-%Y")
END_DATE_STR = END_DATE.strftime("%d-%m-%Y")

def get_state_id(state):
  url = "https://cdn-api.co-vin.in/api/v2/admin/location/states"
  res = json.loads(requests.request("GET", url, headers={}, data={}).text)
  state_id = list(filter(lambda x: x["state_name"].lower() == STATE.lower(), res["states"]))[0]['state_id']
  return state_id

def get_district_id(state_id, district_name):
    url = f"https://cdn-api.co-vin.in/api/v2/admin/location/districts/{state_id}"
    res = json.loads(requests.request("GET", url, headers={}, data={}).text)
    district_id = list(filter(lambda x: x["district_name"].lower() == district_name.lower(), res["districts"]))[0]['district_id']
    return district_id

def get_all_centers(district_id, start_date):
    url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={district_id}&date={start_date}"
    res = json.loads(requests.request("GET", url, headers={}, data={}).text)
    return res


def filter_sessions(e):
    if(e["available_capacity"] > 0 and e["min_age_limit"] <= MIN_AGE):
        return True
    return False

def filter_centers(centers):
    available = []
    for center in centers:
        sessions = list(filter(filter_sessions, center['sessions']))
        if (len(sessions) > 0):
            c = {**center}
            c["sessions"] = sessions
            available.append(c)
    return available


def alert_if_available(district_id, start_date):
    i = 0
    while(True):
        i += 1
        print(f"Attempt: {i} {'-'*50}")
        sd = start_date
        ed = start_date + datetime.timedelta(days=7)
        for x in range(0, WEEKS_TO_CHECK):
            start_date_str = sd.strftime("%d-%m-%Y")
            end_date_str = ed.strftime("%d-%m-%Y")
            print(f"\tChecking from {start_date_str} to {end_date_str}:")

            centers = get_all_centers(district_id, start_date_str)
            ac = filter_centers(centers["centers"])

            if ( len(ac) > 0):
                print(f'\t\tVaccine Available in {DISTRICT} between {start_date_str} and {end_date_str}!')
                with open('vaccine_centers.json', 'w') as f:
                    f.write(json.dumps(ac))
                os.system("vlc --loop alert.mp3")
            else:
                print(f'\t\tNothing Available Yet for {DISTRICT} between {start_date_str} and {end_date_str}!')
            
            sd = ed + datetime.timedelta(days=1)
            ed = sd + datetime.timedelta(days=7)
            
        time.sleep(10)


if (__name__ == '__main__'):
    try:
        district_id = get_district_id(get_state_id(STATE), DISTRICT)
        alert_if_available(district_id, START_DATE)
    except Exception as e:
        print(e)
        print("********************************")
        print("*****  RESTART THE SCRIPT  *****")
        print("********************************")
        os.system("vlc --loop error.mp3")