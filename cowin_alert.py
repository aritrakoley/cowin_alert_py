import requests
import json
import time
import datetime
import os

class CowinAlert:
    def __init__(self):
        # For API Call (User Defined)
        self.STATE = 'West Bengal'
        self.DISTRICT = 'Kolkata'
        self.MIN_AGE = 18

        # For API Call (System Defined)
        self.BASE_URL = 'https://cdn-api.co-vin.in/api/v2'
        self.STATE_URL_PATH = '/admin/location/states'
        self.DISTRICT_URL_PATH = '/admin/location/districts'
        self.SEARCH_URL_PATH = '/appointment/sessions/public/calendarByDistrict'
        self.HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
        }
        
        # For script configuration
        self.WEEKS_TO_CHECK = 3
        self.REPEAT = 1
        self.INPUT_FILE = 'config.json.txt'
        self.OUTPUT_FILE = 'vaccine_available.json'
        self.ADDRESS_CONTAINS = []  # address contains at least one of these words

        # Derived values
        self.START_DATE = datetime.date.today()
        # self.END_DATE = START_DATE + datetime.timedelta(days=7)
        # self.START_DATE_STR = START_DATE.strftime("%d-%m-%Y")
        # self.END_DATE_STR = END_DATE.strftime("%d-%m-%Y")

        # OS dependent command
        self.VLC = 'cvlc'
        if (os.name == 'nt'):
            self.VLC = 'vlc'
        self.ALERT_CMD = f"{self.VLC} --loop alert.mp3"
        self.ERROR_CMD = f"{self.VLC} --loop error.mp3"

    def read_config(self):
        # details = {
        #     'state_name': 'West Bengal',
        #     'district_name': 'Kolkata',
        #     'min_age': 18,
        #     'weeks_to_check': 3,
        #     'repeat_after_mins': 1, 
        #     'output_file': 'vaccine_available.json',
        #     'address_contains': []
        # }
        details = None
        try:
            with open(self.INPUT_FILE, 'r') as f:
                details = json.loads(f.read())
            self.STATE = details['state_name']
            self.DISTRICT = details['district_name']
            self.MIN_AGE = details['min_age']

            self.WEEKS_TO_CHECK = details['weeks_to_check']
            self.REPEAT = details['repeat_after_mins']
            self.OUTPUT_FILE = details['output_file']
            self.ADDRESS_CONTAINS = details['address_contains'] 
        except Exception as e:
            print('config.json.txt could not be read... using default config')
        finally:
            return details

    def get_state_id(self):
        url = f'{self.BASE_URL}{self.STATE_URL_PATH}'
        res = json.loads(requests.request("GET", url, headers=self.HEADERS, data={}).text)
        state_id = list(filter(lambda x: x["state_name"].lower() == self.STATE.lower(), res["states"]))[0]['state_id']
        return state_id


    def get_district_id(self, state_id):
        url = f"{self.BASE_URL}{self.DISTRICT_URL_PATH}/{state_id}"
        res = json.loads(requests.request("GET", url, headers=self.HEADERS, data={}).text)
        district_id = list(filter(lambda x: x["district_name"].lower() == self.DISTRICT.lower(), res["districts"]))[0]['district_id']
        return district_id


    def get_all_centers(self, district_id, start_date):
        url = f"{self.BASE_URL}{self.SEARCH_URL_PATH}?district_id={district_id}&date={start_date}"
        res = json.loads(requests.request("GET", url, headers=self.HEADERS, data={}).text)
        return res


    def filter_centers(self, centers):

        def filter_sessions(e):
            if(e["available_capacity"] > 0 and e["min_age_limit"] <= self.MIN_AGE):
                return True
            return False

        available = []
        for center in centers:
            # (1) Match Address
            matches = [ m for m in self.ADDRESS_CONTAINS if m.lower() in center['address'].lower() ]
            if (len(self.ADDRESS_CONTAINS) > 0 and len(matches) == 0): continue

            # (2) Check for available sessions which match filters
            sessions = list(filter(filter_sessions, center['sessions']))
            if (len(sessions) > 0):
                c = {**center}
                c["sessions"] = sessions
                available.append(c)
        return available

    def  run_alert(self):
        # (0) Read Config
        self.read_config()

        # (1) SHOW DETAILS TO USER ---------------------------------------
        print(f'''
            Searching for Vaccine Availability:
            State: {self.STATE}
            District: {self.DISTRICT}
            Address Contains: {self.ADDRESS_CONTAINS}
            Minimum Age: {self.MIN_AGE}
            Start Date: {self.START_DATE.strftime("%d-%m-%Y")}
            Checking next {self.WEEKS_TO_CHECK} weeks from Start Date
            Repeating every {self.REPEAT} minute(s)...
            ( Press CTRL + C or CTRL + D or CTRL + Z to stop alarm/script )
        ''')

        # (2) CALL APIs ON LOOP and ALERT on ERROR or AVAILABILITY ---------------------------------------
        try:
            district_id = self.get_district_id(self.get_state_id())

            # alert_if_available
            i = 0
            while(True):
                i += 1
                print(f"Attempt: {i} {'-'*50}")
                sd = self.START_DATE
                ed = self.START_DATE + datetime.timedelta(days=7)
                for x in range(0, self.WEEKS_TO_CHECK):
                    start_date_str = sd.strftime("%d-%m-%Y")
                    end_date_str = ed.strftime("%d-%m-%Y")
                    print(f"\tChecking from {start_date_str} to {end_date_str}:")

                    centers = self.get_all_centers(district_id, start_date_str)
                    ac = self.filter_centers(centers["centers"])

                    if (len(ac) > 0):
                        print(
                            f'\t\tVaccine Available in {self.DISTRICT} between {start_date_str} and {end_date_str}!')
                        with open(self.OUTPUT_FILE, 'w') as f:
                            f.write(json.dumps(ac))
                        os.system(self.ALERT_CMD)
                    else:
                        print(
                            f'\t\tNothing Available Yet for {self.DISTRICT} between {start_date_str} and {end_date_str}!')

                    sd = ed + datetime.timedelta(days=1)
                    ed = sd + datetime.timedelta(days=7)

                print('( Press CTRL + C or CTRL + D or CTRL + Z to stop alarm/script )')
                time.sleep(60 * self.REPEAT)

        except Exception as e:
            print(e)
            print("********************************")
            print("*****  RESTART THE SCRIPT  *****")
            print("********************************")
            os.system(self.ERROR_CMD)

if (__name__ == '__main__'):
    ca = CowinAlert()
    ca.run_alert()