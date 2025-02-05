from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
import json
import config
import requests
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
import geocoder
import random

geolocator = Nominatim(user_agent="my_geocoding_app")

def get_coordinates(city_name):
    try:
        # Geocode the city name
        location = geolocator.geocode(city_name)
        if location:
            return location.latitude, location.longitude
        else:
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


class TripPlannerService:
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=config.GROQ_API_KEY,
            model=config.MODEL,
            temperature=0.7,
        )

    def generate_itinerary(self, destination, trip_duration, activities):
        """
        Generate a travel itinerary based on the provided details.
        """
        from langchain.prompts import PromptTemplate

        prompt_generate_itinerary = PromptTemplate.from_template(
    """### ITINERARY GENERATION INSTRUCTIONS:

    Generate a **detailed travel itinerary** based on the following details:

    - **Destination:** {destination}
    - **Trip Duration:** {trip_duration} days
    - **Preferred Activities:** {activities}

    #### Structure the itinerary as follows:
    1. **Destination Title** 🏙️
    2. **Daily Itinerary:** Provide a well-planned schedule for each day.
       - Include **3-5 engaging yet concise** activity descriptions per day.
       - Mention **transportation details** (e.g., bus 🚌, train 🚆, boat ⛵, cab 🚖, walking 🚶).
       - Keep descriptions **short and engaging** (1-2 sentences per activity).
       - Use **emojis** to make it visually appealing.

    #### **OUTPUT FORMAT:** Return **only** a valid JSON object with the following keys:
    {{
      "destination": "{destination}",
      "daily_activities": [
        ["Day 1 activities..."],
        ["Day 2 activities..."],
        ["Day 3 activities..."]
      ]
    }}
    """
      )



        chain_generate_itinerary = prompt_generate_itinerary | self.llm
        response = chain_generate_itinerary.invoke(
            input={
                'destination': destination,
                'trip_duration': trip_duration,
                'activities': activities,
            }
        )

        try:
            itinerary_response = response.content
            start_index = itinerary_response.find("{")
            end_index = itinerary_response.rfind("}") + 1
            json_string = itinerary_response[start_index:end_index]
            itinerary = json.loads(json_string)
            return itinerary
        except json.JSONDecodeError as e:
            return {"error": f"Error decoding JSON: {e}"}
        
    def get_travel_instructions(self, destination, destination1):
        """
        Generate instructions on how to travel between two destinations (e.g., "How to travel from {destination} to {destination1}")
        """
        prompt_travel_instructions = PromptTemplate.from_template(
            """
            ### TRAVEL INSTRUCTIONS INSTRUCTIONS:
            Provide detailed instructions on how to travel from {destination} to {destination1}. Include the most common mode of transportation and estimated travel time and distance.

            The answer should include:
            1. Recommended mode of transportation (e.g., car, flight, train, etc.)
            2. Estimated travel time
            3. Estimated distance
            4. Possible route or directions (optional)

            ONLY return valid JSON with the following keys:
            - `mode_of_transportation` (string): The recommended mode of transport.
            - `estimated_travel_time` (string): Estimated time to travel.
            - `estimated_distance` (string): Estimated distance between the two destinations.
            - `route_details` (optional string): Directions or routes if available.
            ### JSON FORMAT ONLY:
            """
        )

        chain_travel_instructions = prompt_travel_instructions | self.llm
        response = chain_travel_instructions.invoke(
            input={
                'destination': destination,
                'destination1': destination1,
            }
        )

        try:
            instructions_response = response.content
            start_index = instructions_response.find("{")
            end_index = instructions_response.rfind("}") + 1
            json_string = instructions_response[start_index:end_index]
            instructions = json.loads(json_string)
            return instructions
        except json.JSONDecodeError as e:
            return {"error": f"Error decoding JSON: {e}"}

    def scrape_destination_info(self, destination):
        #  location = geolocator.geocode("me")
        g = geocoder.ip('me')

        coordinates = get_coordinates(destination)
        coordinates1 = get_coordinates('paldi,Ahmedabad,gujarat')

        print(coordinates)
        print(coordinates1)
    
        search_url = f"https://www.google.com/search?q={destination} travelling place&tbm=isch"
        print("dhaval donkey")
        print(destination)
        print(f"Latitude: {g.latlng[0]}, Longitude: {g.latlng[1]}")

        search_map_dist = f""; 
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

        response = requests.get(search_url, headers=headers)
        
        if response.status_code != 200:
            return {"error": "Failed to retrieve data from Google."}

        soup = BeautifulSoup(response.text, 'html.parser')

        images = []
        for img in soup.find_all('img'):
            img_url = img.get('src')
            if img_url and img_url.startswith('http'):
                images.append(img_url)

        info_snippets = []
        for div in soup.find_all('div', class_='BNeawe s3v9rd AP7Wnd'):
            info_snippets.append(div.get_text())

        return {
            "images": images[:6], 
            "coordinates": coordinates,
            "coordinates1": coordinates1
        }
    
    def scrape_train_schedule(self, source, destination):
        """Scrape train schedule between stations"""
        try:
            # Format destination for URL
            formatted_dest = destination.replace(" ", "-").lower()
            
            USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
]

            url = f"https://www.makemytrip.com/railways/{source}-{formatted_dest}-train-tickets.html"
            
            headers = {
                "User-Agent": random.choice(USER_AGENTS)
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            return self.parse_train_schedule(response.text)
            
        except Exception as e:
            print(f"Train scraping error: {e}")
            return None

    def parse_train_schedule(self, html_content):
        """Parse train schedule from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        trains = []
        
        for train in soup.select('li.trainList'):
            try:
                name_tag = train.select_one('.trainNameNum a.trainName')
                number_tag = train.select_one('.trainNameNum .trainNumber')
                days_tag = train.select_one('.weeklySchedule')
                
                time_tags = train.select('.startDepartTime .timeText')
                station_codes = train.select('.stationCode')
                duration_tag = train.select_one('.travelHrs')
                
                days = [day['title'] 
                       for day in days_tag.select('span[title]') 
                       if 'greenText' in day.get('class', [])]
                
                train_data = {
                    'name': name_tag.text.strip(),
                    'number': number_tag.text.strip('#').strip(),
                    'departure': {
                        'time': time_tags[0].text.strip(),
                        'station': station_codes[0].text.strip()
                    },
                    'arrival': {
                        'time': time_tags[1].text.strip(),
                        'station': station_codes[1].text.strip()
                    },
                    'duration': ' '.join([
                        part.text.strip() 
                        for part in duration_tag.select('.durationPart')
                    ]),
                    'runs_on': days
                }
                
                trains.append(train_data)
                
            except Exception as e:
                print(f"Error parsing train: {e}")
                continue
                
        return trains