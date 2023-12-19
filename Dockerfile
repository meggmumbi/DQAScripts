# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app


# Create the sources.list file
#RUN echo "deb http://debian.ftp.acc.umu.se/debian/ buster main" > /etc/apt/sources.list

# Install any needed packages specified in requirements.txt
RUN apt-get update && \
    apt-get install -y unixodbc unixodbc-dev && \
    rm -rf /var/lib/apt/lists/*


RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Run script.py when the container launches
CMD ["python", "/app/main.py", "./checksTxCurr.py", "./checkMeaningfulVisits.py", "./checkDuplicatePatientIds.py", "./checkDateCreatedDateModified.py"]
