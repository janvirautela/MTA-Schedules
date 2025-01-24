import unittest #python lib for writing unit tests
#import functions we want to test 
from transit_service.app import find_closest_station, get_lirr_data, get_metro_north_data
import pytest #testing framework
from transit_service.app import app #for testing http endpts from app

#expects test case classes to inherit from TestCase, contains all individual test methods
class TestTransitService(unittest.TestCase):
    def test_find_closest_station(self):
        #known coordinates, NYC
        closest_station = find_closest_station(40.7128, -74.0060)
        self.assertEqual(closest_station, "R16")  #expecting R16 as closest station ID

#pytest allows to set up reusable test res
@pytest.fixture #create a test client for making requests to the Flask app
def client(): #initializes Flask test client, app.test_client(), make req to Flask app
    with app.test_client() as client:
        yield client #returns test client for use in the tests

#test /api/transit endpt 
#send valid request with origin station ID: R16, destination station ID: N01 + coordinates
def test_get_transit_schedules(client):
    response = client.post('/api/transit', json={ #send POST req to /api/transit endpt w JSON data
        "origin_station_id": "R16",
        "coordinates": {"latitude": 40.7128, "longitude": -74.0060},
        "destination_station_id": "N01"
    })
    assert response.status_code == 200 #checks for success 
    assert 'next_schedules' in response.get_json() #checks that resp body contains key 'next_schedules'

#checks what happens when coordinates are missing 
def test_get_transit_schedules_missing_coordinates(client):
    #missing coordinates
    response = client.post('/api/transit', json={
        "origin_station_id": "R16",
        "destination_station_id": "N01"
    })
    assert response.status_code == 400 #expect bad req error 
    assert response.get_json() == {"error": "Coordinates are required"} #checks that resp has expected error message

def test_get_lirr_data(): #verifies get_lirr_data returns valid data
    lirr_data = get_lirr_data()
    assert lirr_data is not None  #is data returned
    assert isinstance(lirr_data, dict)  #is it a dict

def test_get_metro_north_data(): #verifies get_metro_north_data returns valid data
    metro_north_data = get_metro_north_data()
    assert metro_north_data is not None  #is data returned
    assert isinstance(metro_north_data, dict)  #is it a dict

def find_closest_station(latitude, longitude):
    #station data
    stations = [
        {"station_id": "R16", "latitude": 40.7128, "longitude": -74.0060},
        {"station_id": "CH01", "latitude": 40.7127, "longitude": -74.0059},
    ]
    
    closest_station = None
    min_distance = float('inf')

    for station in stations:
        #calculate distance 
        distance = ((latitude - station['latitude']) ** 2 + (longitude - station['longitude']) ** 2) ** 0.5
        if distance < min_distance:
            min_distance = distance
            closest_station = station['station_id']

    return closest_station

if __name__ == '__main__': #to run all tests, runs any methods in class that start with test_ 
    unittest.main()
