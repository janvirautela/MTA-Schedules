import os #operating system 
import logging 
from logging.handlers import RotatingFileHandler #logging events 
from dotenv import load_dotenv #load environment variables from .env 
import requests #to make HTTP requests to MTA API, talk 
from google.transit import gtfs_realtime_pb2 #to parse Google Transit Feed Messages, containing real-time transit information
from flask import Flask, request, jsonify #framework to build REST api service, create web api for send and receive
from geopy.geocoders import Nominatim #geographical calculations, coordinate distance
import datetime #to work with dat and time 
import geopy.distance
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="my_geocoder")

#used for testing with a known set of coordinates
#reverses geocodes of coordinates (latitude, longitude) into a human-readable address
location = geolocator.reverse("40.7128, -74.0060", exactly_one=True)
print(location) #printing to verify 
stations = [
    {"name": "City Hall", "latitude": 40.7127, "longitude": -74.0059, "station_id": "CH01", "gtfs_stops": ["S25", "S26", "S27"], "alternative_ids": ["R16"]},
    {"name": "Times Square", "latitude": 40.7580, "longitude": -73.9855, "station_id": "TSQ01", "gtfs_stops": ["S29", "S30", "S31"]},
    # Add more stations with their GTFS stop patterns
    {"name": "Grand Central", "latitude": 40.7527, "longitude": -73.9772, "station_id": "GC01", "gtfs_stops": ["S20", "S21", "S22"]},
    {"name": "Penn Station", "latitude": 40.7505, "longitude": -73.9934, "station_id": "PS01", "gtfs_stops": ["S15", "S16", "S17"]}
]#each station is as a dict with: name, latitude, longitude, primary station ID

#configures comprehensive logging 
def setup_logging():
    #creates a logger named 'transit_api' to record messages at various levels
    logger = logging.getLogger('transit_api')
    logger.setLevel(logging.DEBUG)

    #console handler, will show log in console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    #file handler, shows logs in transit_api.log 
    file_handler = RotatingFileHandler('transit_api.log', maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger

load_dotenv()  #load environment variables from .env file

app = Flask(__name__) #starts web application

#setup logging
logger = setup_logging()


# Read subway API URLs from .env and split into a list
SUBWAY_API_URLS = os.getenv('SUBWAY_API_URLS').split(',')

BUS_API_KEY = os.getenv('BUS_API_KEY')

#initialize Nominatim geocoder. Object used to convert coordinates into addresses and find the nearest stations
geolocator = Nominatim(user_agent="my_geocoder")

@app.route('/api/transit', methods=['POST']) #triggered when a POST request is made to the /api/transit endpoint
def get_transit_schedules(): #processes input data, coordinates, station IDs, returns transit schedules
    logger.info("Received transit schedule request")
    
    data = request.json
    coordinates = data.get('coordinates')
    origin_station_id = data.get('origin_station_id')
    destination_station_id = data.get('destination_station_id')
    #here we extract coordinates, origin_station_id, and destination_station_id from the request data

    logger.debug(f"Request details - Origin: {origin_station_id}, Destination: {destination_station_id}, Coordinates: {coordinates}")

    if not coordinates: #didn't provide coordinates 
        logger.error("Coordinates are required")
        return jsonify({"error": "Coordinates are required"}), 400 #logs error, 400 is bad req

    try:
        latitude = float(coordinates.get('latitude'))
        longitude = float(coordinates.get('longitude'))
    except (ValueError, TypeError):
        logger.error(f"Invalid coordinates format: {coordinates}")
        return jsonify({"error": "Invalid coordinates format"}), 400

    #if origin_station_id or destination_station_id is not provided, call find_closest_station() to find nearest stations based on the coordinates
    #find closest stations if not provided
    if not origin_station_id:
        closest_origin_station_id = find_closest_station(latitude, longitude)
    else:
        closest_origin_station_id = origin_station_id

    if not destination_station_id:
        #exclude_stations makes sure origin station isn't used as destination
        closest_destination_station_id = find_closest_station(latitude, longitude, exclude_station=closest_origin_station_id)
    else:
        closest_destination_station_id = destination_station_id

    logger.debug(f"Closest stations - Origin: {closest_origin_station_id}, Destination: {closest_destination_station_id}")

    # Fetch subway data
    logger.info("Fetching subway data")
    #get rt subway schedules
    subway_data = get_subway_data(closest_origin_station_id, closest_destination_station_id)
    
    logger.info("Fetching bus data")
    #get rt bus schedules
    bus_data = get_bus_data()

    logger.info("Fetching LIRR data")
    #get LIRR and Metro N data
    lirr_data = get_lirr_data()

    logger.info("Fetching Metro North data")
    #get Metro N data
    metro_north_data = get_metro_north_data()

    #initialize the response list
    next_schedules = []

    # process subway data
    logger.info(f"Processing {len(subway_data)} subway schedules")
    for subway in subway_data:
        next_schedules.append({
            "transit_mode": "subway",
            "eta_origin": subway['eta_origin'],
            "eta_destination": subway['eta_destination']
        })

    #process bus data
    logger.info("Processing bus data")
    for bus in bus_data.get('schedules', []):
        if bus['origin_station_id'] == closest_origin_station_id and bus['destination_station_id'] == closest_destination_station_id:
            next_schedules.append({
                "transit_mode": "bus",
                "eta_origin": bus['eta_origin'],
                "eta_destination": bus['eta_destination']
            })

    #process LIRR data
    if lirr_data:
        for lirr_schedule in lirr_data.get('schedules', []):  
            next_schedules.append({
                "transit_mode": "lirr",
                "eta_origin": lirr_schedule.get('eta_origin'),  
                "eta_destination": lirr_schedule.get('eta_destination')  
            })

    #process Metro North data
    if metro_north_data:
        for metro_north_schedule in metro_north_data.get('schedules', []):  
            next_schedules.append({
                "transit_mode": "metro_north",
                "eta_origin": metro_north_schedule.get('eta_origin'), 
                "eta_destination": metro_north_schedule.get('eta_destination')  
            })


    # Create the final response
    response = {
        "next_schedules": next_schedules
    }

    logger.info(f"Returning {len(next_schedules)} transit schedules")
    return jsonify(response) #puts schedules into JSON resp and sends back

#helper func, finds closest station to the given coordinates
def find_closest_station(latitude, longitude, exclude_station=None):
    closest_station = None
    min_distance = float('inf')  #initialize with a large value, any dist will be smaller than this
    #used to keep track of the closest station and distance

    #iterate through stations list, calculate distance between each station and provided coordinates using geopy.distance.distance()
    for station in stations:
        #skip the excluded station (default is None) if provided
        if exclude_station and station['station_id'] == exclude_station: #if exclude_station provided. Skips over current startion
            continue

        #create tuples because the func expects two tuples
        station_coords = (station['latitude'], station['longitude'])
        user_coords = (latitude, longitude)
        
        distance = geopy.distance.distance(user_coords, station_coords).km #find distance between and store in km
        if distance < min_distance: #is current dist less than mindistance? 
            min_distance = distance
            closest_station = station #update to current closest station
    
    if closest_station:
        return closest_station['station_id'] #if found, return id
    else:
        logger.warning("No station found")
        return None
    #returns station_id of closest station or None if no station found

#for extracting station ID from address
def extract_station_id(address):
    logger.debug(f"Extracting station ID from address: {address}")
    #look for common station keywords in the address
    station_keywords = ["Station", "Subway", "Train", "Metro"]
    for keyword in station_keywords:
        if keyword in address:
            #if keyword found, extract part of the address before the keyword as station ID, else return None
            station_id = address.split(keyword)[0].strip()
            logger.info(f"Extracted station ID: {station_id}")
            return station_id
    logger.warning("No station found in address")
    return None

#to get GTFS stop patterns for a specific station ID
#tell the system which stops are relevant to certain station, stops that a service will pass through
#to identify routes from origin_station_id -> destination_station_id, need to know stops corresponding to stations
#using these stop patterns, identify if subway trip involves origin and destination stations
def get_gtfs_stops_for_station(station_id): #get stop pattern for input station
    for station in stations:
        #loop through stations, if station_id matches or is substring of station's ID
        if station_id == station['station_id'] or station_id in station.get('alternative_ids', []):
            return station.get('gtfs_stops', []) #return stop patterns for station 
    return [] #return list of stops

def get_subway_data(origin_station_id, destination_station_id): #gets subway scheds
    subway_data = [] #will hold final result
    logger.info(f"Searching for subway routes between {origin_station_id} and {destination_station_id}")

    #get GTFS stop patterns for each station
    origin_stops = get_gtfs_stops_for_station(origin_station_id)
    destination_stops = get_gtfs_stops_for_station(destination_station_id)

    #logging for debugging
    logger.info(f"Origin stop patterns: {origin_stops}")
    logger.info(f"Destination stop patterns: {destination_stops}")

    for url in SUBWAY_API_URLS: #loop over subway feed 
        try:
            response = requests.get(url) #send get req to get subway data
            if response.status_code == 200: #200 means success 
                feed = gtfs_realtime_pb2.FeedMessage() 
                feed.ParseFromString(response.content) #decode the raw rt feed into readable data with func

                for entity in feed.entity:
                    if entity.HasField('trip_update'): #trip_update has updates on subway
                        trip_update = entity.trip_update
                        stop_time_updates = trip_update.stop_time_update #list of stop updates
                        
                        for origin_idx, origin_stop in enumerate(stop_time_updates):
                            #if stop ID in origin_stops match that of stop ID in stop_time_updates, subway passes through origin. Any stop ID of origin matches current
                            origin_match = any(stop_pattern in origin_stop.stop_id for stop_pattern in origin_stops)
                            
                            #once origin stop matched, look for dest stop
                            #look at all next stops after origin stop
                            if origin_match:
                                for dest_idx, dest_stop in enumerate(stop_time_updates[origin_idx+1:], start=origin_idx+1):
                                    dest_match = any(stop_pattern in dest_stop.stop_id for stop_pattern in destination_stops)
                                    
                                    #if both match, get arrival time for both 
                                    if dest_match:
                                        try:
                                            origin_time = origin_stop.arrival.time if origin_stop.HasField('arrival') else None
                                            dest_time = dest_stop.arrival.time if dest_stop.HasField('arrival') else None
                                            
                                            #when you get both times, create a fict with required result info  
                                            if origin_time and dest_time:
                                                subway_data.append({ #append info to have multiple options
                                                    "transit_mode": "subway",
                                                    "eta_origin": datetime.datetime.fromtimestamp(origin_time).strftime('%Y-%m-%d %H:%M:%S'),
                                                    "eta_destination": datetime.datetime.fromtimestamp(dest_time).strftime('%Y-%m-%d %H:%M:%S')
                                                })
                                        except Exception as time_error: #error handling: if error faced in processing times, log it
                                            logger.error(f"Time parsing error: {time_error}")
                        
        except Exception as e: #error handling: any error when processing url, like invalid data, log it
            logger.error(f"Error processing {url}: {e}") 

    logger.info(f"Found {len(subway_data)} subway routes") #log # of routes 
    return subway_data #return list with scheds


def get_bus_data():
    bus_api_url = "https://bustime.mta.info/api/where/routes-for-agency/MTA%20NYCT.json"
    api_key = os.getenv('BUS_API_KEY') #getting key from .env

    logger.info("Fetching bus routes")

    # Add the API key as a query parameter
    response = requests.get(f"{bus_api_url}?key={api_key}") #send get req to bus endpt. How key is passed to api
    
    if response.status_code == 200: #if success 
        try:
            bus_data = response.json() #parse json resp, convert it into python dict
            logger.info(f"Retrieved bus data successfully")
            return bus_data #has route info
        except ValueError: #error handling: issue parsing data, ex html format
            logger.error(f"Invalid JSON response from {bus_api_url}")
            return None
    else: #other failure 
        logger.error(f"Failed to fetch bus data, Status code: {response.status_code}")
        return None

# Read LIRR and Metro North API URLs from .env
LIRR_API_URL = os.getenv('LIRR_API_URL')
METRO_NORTH_API_URL = os.getenv('METRO_NORTH_API_URL')

def get_lirr_data():
    logger.info("Fetching LIRR data") 
    try:
        response = requests.get(LIRR_API_URL) #sends GET request URL, endpoint
        if response.status_code == 200: #if success
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content) #takes raw resp content, converts it into structured object, feed
            
            lirr_schedules = []
            for entity in feed.entity: #loop through each entity in feed.entity collection
                if entity.HasField('trip_update'): #if has field trip_update, entity is related to train trip update
                    #store in trip_update
                    trip_update = entity.trip_update
            return {"schedules": lirr_schedules} #lirr_schedules list returned as a dict 
        else: #not success, then log error
            logger.error(f"Failed to fetch LIRR data, Status code: {response.status_code}")
            return None
    except Exception as e: #log exceptions
        logger.error(f"LIRR data fetch error: {e}")
        return None

def get_metro_north_data():
    logger.info("Fetching Metro North data")
    try:
        response = requests.get(METRO_NORTH_API_URL) #send GET req to api endpt
        if response.status_code == 200: #if success 
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content) #parse to convert raw binary response into a structured feed object
            
            metro_north_schedules = []
            for entity in feed.entity: #loop over feed.entity
                if entity.HasField('trip_update'): #entity contains trip_update data, extract trip_update and stop_time_update
                    trip_update = entity.trip_update
                    stop_time_updates = trip_update.stop_time_update
                    
                    #loops over each stop_time_update, compares every pair of origin and destination stp
                    for origin_idx, origin_stop in enumerate(stop_time_updates): #iterating over origin_stop
                        for dest_idx, dest_stop in enumerate(stop_time_updates[origin_idx+1:], start=origin_idx+1): #iterating over dest_stop
                            try:
                                #extract arrival time for origin_stop and dest_stop
                                origin_time = origin_stop.arrival.time if origin_stop.HasField('arrival') else None
                                dest_time = dest_stop.arrival.time if dest_stop.HasField('arrival') else None
                                
                                if origin_time and dest_time: #if success for both 
                                    metro_north_schedules.append({ #append for multiple sched
                                        "transit_mode": "metro_north",
                                        "eta_origin": datetime.datetime.fromtimestamp(origin_time).strftime('%Y-%m-%d %H:%M:%S'), #converts timestamp into a human readable date+time 
                                        "eta_destination": datetime.datetime.fromtimestamp(dest_time).strftime('%Y-%m-%d %H:%M:%S')
                                    })
                            except Exception as time_error: #error handling: ex, invalid timestamp, log it
                                logger.error(f"Metro North time parsing error: {time_error}")
            
            return {"schedules": metro_north_schedules} #returns dict w key schedules
        else: #no success, log it
            logger.error(f"Failed to fetch Metro North data, Status code: {response.status_code}")
            return None
    except Exception as e: #log exceptions, ex parsing error
        logger.error(f"Metro North data fetch error: {e}")
        return None


if __name__ == '__main__': #runs when script is run directly 
    logger.info("Starting Transit API application")
    app.run(debug=True) #runs Flask server w debug mode
