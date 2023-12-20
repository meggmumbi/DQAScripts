# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app


# Install any needed packages specified in requirements.txt
RUN apt-get update && \
    apt-get install -y unixodbc unixodbc-dev  freetds-dev && \
    rm -rf /var/lib/apt/lists/*

# Install the SQL Server ODBC driver
RUN apt-get update && \
    apt-get install -y odbcinst1debian2 && \
    rm -rf /var/lib/apt/lists/*

COPY odbcinst.ini /etc/odbcinst.ini
COPY odbc.ini /etc/odbc.ini

RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Run script.py when the container launches
CMD ["python", "/app/main.py", "./checksTxCurr.py", "./checkMeaningfulVisits.py", "./checkDuplicatePatientIds.py", "./checkDateCreatedDateModified.py"]
