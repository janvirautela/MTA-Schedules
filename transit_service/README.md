#Public Transit Service API for accessing transit data like schedules or routes

#Description
RESTful API for public transit services.

#Environment Requirements: Flask, requests, python-dotenv

#Operating System: run on any operating system that supports Docker: Linux,Windows, macOS

#Dependencies: Python 3.9+, Docker

#Running the Application
#Locally:
1. Clone repo.
2. Navigate to project directory.
3. Create a virtual environment and activate it.
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the application:
   ```bash
   python app.py
   ```

#Using Docker
1. Build the Docker image:
   ```bash
   docker build -t transit-service .
   ```
2. Run the Docker container:
   ```bash
   docker run -p 5000:5000 --env-file .env transit-service
   ```

#Pulling the Docker Image
Use the following command:
bash: docker pull yourusername/transit-service:latest

#API Documentation
Provides transit schedule information for subways and buses in New York City.

#Base URL
```
http://localhost:5000/api
```

#Environment Variables
Before running the application, create a `.env` file in the project root with the following variables:

```
BUS_API_KEY=6228bb5d-b3ff-49b2-9a74-0b3f3738d9e8
LIRR_API_URL= https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/lirr%2Fgtfs-lirr
METRO_NORTH_API_URL=https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/mnr%2Fgtfs-mnr
SUBWAY_API_URLS=https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace,https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g,https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw,https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs,https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm,https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz,https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l,https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si

```

#POST /transit
- **Description**: Get the next transit schedules based on origin and destination.
- **Request Body**:
  ```json
  {
    "origin_station_id": "string",
    "coordinates": {
      "latitude": "string",
      "longitude": "string"
    },
    "destination_station_id": "string"
  }
  ```
- **Response**:
  - **Success (200)**:
    ```json
    {
      "next_schedules": [
        {
          "transit_mode": "rail",
          "eta_origin": "string",
          "eta_destination": "string"
        }
      ]
    }
    ```
  - **Error (400)**:
    ```json
    {
      "error": "Invalid input"
    }
    ```

#Example Request
```bash
curl -X POST http://localhost:5000/api/transit \
-H "Content-Type: application/json" \
-d '{
  "origin_station_id": "123",
  "coordinates": {
    "latitude": "40.7128",
    "longitude": "-74.0060"
  },
  "destination_station_id": "456"
}'
```

#Additional Information
- **Logging**: The application logs requests and errors to `transit_api.log` for debugging purposes.
- **Dependencies**: Ensure you have the following Python packages installed:
  - Flask
  - requests
  - python-dotenv
  - geopy
  - google.transit (for GTFS data)

#Testing
- Run testing file: open terminal, navigate to directory where test_app.py is located. If you are using virtual env, ex., venv, activate it by typing this in Bash: source venv/bin/activate for Mac or for Windows: venv\Scripts\activate 
- Bash to run file: python -m unittest transit_service/test_app.py or pytest transit_service/test_app.py
- See output in terminal 

##Alternate testing in Postman: 
- Download Postman to desktop or login
- Create POST req to this url: http://127.0.0.1:5000/api/transit
- Select Raw and JSON. In body paste this: {
  "origin_station_id": "TSQ01", 
  "coordinates": {
    "latitude": "40.7580",
    "longitude": "-73.9855"
  },
  "destination_station_id": "R16" 
} 


#Network Configuration
- The application listens on port 5000. Ensure this port is available on your host machine.
