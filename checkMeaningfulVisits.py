# Import the pika library for RabbitMQ
import pika
import json
import pyodbc

# Establish a connection to the RabbitMQ server
credentials = pika.PlainCredentials('brian', 'brian')
connection = pika.BlockingConnection(pika.ConnectionParameters('10.230.50.63', 5672, 'spot2', credentials))
channel = connection.channel()

# Declare the exchange and the queue to subscribe to
channel.exchange_declare(exchange='spot.exchange', exchange_type='direct')
channel.queue_declare(queue='completenotice.queue', durable=True)

# Bind the queue to the exchange with the routing key
channel.queue_bind(exchange='spot.exchange', queue='completenotice.queue', routing_key='completenotice.route')


# Define a callback function to handle the messages
def callback(ch, method, properties, body):
    print(f"Payload: {body}")

    # Acknowledge the message
    ch.basic_ack(delivery_tag=method.delivery_tag)

    decoded_body = body.decode('utf-8')

    # Replace single quotes with double quotes in the payload
    corrected_body = decoded_body.replace("'", "\"")

    # Parse the payload as a JSON object
    payload = json.loads(corrected_body)

    # Get the MFL Code from the payload
    mfl_code = payload['MFL Code']
    name = payload['Facility']

    if payload.get('Docket') == 'NDWH':

        conn = pyodbc.connect('Driver={SQL Server};'
                              'Server=10.230.50.83;'
                              'Database=DWAPICentral;'
                              'UID=dwh_readonly;'
                              'PWD=c0nstella;')

        # Create a cursor object
        cursor = conn.cursor()

        # Execute the query with the MFL Code
        query = f"""SELECT COUNT(*)
          FROM PatientVisitExtract
          WHERE visitType = 'scheduled' AND nextAppointmentDate IS NULL AND siteCode = {mfl_code};"""

        cursor.execute(query)

        # Fetch the results and print them
        results = cursor.fetchall()
        print(f"Results for MFL Code {mfl_code}:")
        for row in results:
            print(row)

        # Connect to the SQL Server database where you want to save the results
        db_connection = pyodbc.connect('Driver={SQL Server};'
                                       'Server=PAL-5CG2114M0C;'
                                       'Database=DwapiCentral;'
                                       'UID=sa;'
                                       'PWD=Megg96Megg;')

        # Create a cursor object for the database connection
        db_cursor = db_connection.cursor()

        merge_query = """
        MERGE INTO DwapiCentral_DQA AS target
        USING (VALUES (?, ?,?,?)) AS source (MFL_Code,Name, Indicator, Value)
        ON target.MFL_Code = source.MFL_Code
        WHEN MATCHED THEN
            UPDATE SET target.Value = source.Value
        WHEN NOT MATCHED THEN
            INSERT (MFL_Code, Name,Indicator,Value) VALUES (source.MFL_Code,source.Name,source.Indicator,source.Value);
        """

        # Iterate through the results and insert them into the database
        for row in results:
            _visits = row[0]
            db_cursor.execute(merge_query, mfl_code, name, "Meaningful_Visits", _visits)

        # Commit the changes to the database
        db_connection.commit()

        # Close the database connection
        db_connection.close()

        # Close the connection
        conn.close()


# Start consuming the messages from the queue
channel.basic_consume(queue='completenotice.queue', on_message_callback=callback)

# Wait for messages until interrupted
print('Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
