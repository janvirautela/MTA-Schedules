#specifies base image for Docker container, official image from Docker Hub
FROM python:3.9-slim

#sets working directory inside Docker container to /app, tells Docker where subsequent commands will be run, in container
WORKDIR /app

#copy the requirements file and install dependencies
COPY requirements.txt .
#pip install reads requirements.txt file and installs
RUN pip install --no-cache-dir -r requirements.txt

#copies entire contents of the current directory into the working directory (/app) of container
COPY . .

#container will listen on port 5000
EXPOSE 5000

#command to run the application, when Docker container is started
CMD ["python", "app.py"]
