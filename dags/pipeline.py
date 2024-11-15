import datetime

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator

import pandas as pd
import random
import pymongo
import psycopg2
from psycopg2.extras import execute_values
import email
from email import policy
from email.parser import BytesParser
import base64

client = pymongo.MongoClient('mongodb://admin:admin@mongodb:27017/')
db = client['lab9']
collection = db['email']

# Kết nối PostgreSQL
conn = psycopg2.connect(
    dbname="lab9",
    user="airflow",
    password="airflow",
    host="postgres",
    port=5432
)
pg_cursor = conn.cursor()

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS Emails (
  id BIGSERIAL PRIMARY KEY,
  message_id VARCHAR(255),
  subject VARCHAR(255),
  body TEXT,
  mime_version VARCHAR(50),
  content_type VARCHAR(100),
  content_transfer VARCHAR(50),
  date TIMESTAMP,
  x_from VARCHAR(255),
  x_folder VARCHAR(255),
  x_origin VARCHAR(255),
  x_filename VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS Users (
  id BIGSERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE,
  name VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS Recipients (
  id BIGSERIAL PRIMARY KEY,
  email_id BIGINT REFERENCES Emails(id),
  user_id BIGINT REFERENCES Users(id),
  recipient_type VARCHAR(10)
);
"""

url = 'https://raw.githubusercontent.com/tnhanh/data-midterm-17A/refs/heads/main/email.csv'
data_path = '/opt/airflow/data/email.csv'
df = pd.read_csv(data_path)

def get_random_data(data):
    random_seed = int(datetime.datetime.now().timestamp())
    data = data.sample(n=200, random_state=random_seed)
    return data

def insert_data(data):
    data.reset_index(inplace=True)
    data_dict = data.to_dict("records")
    # check if data already exists in the collection and update it
    for i in data_dict:
        if collection.find_one({'file': i['file']}) is None:
            collection.update_one({'index': i['index'], "processed": False}, {"$set": i}, upsert=True)
    print('Data inserted successfully')

def create_table():
    pg_cursor.execute(CREATE_TABLE_SQL)
    conn.commit()
    print('Tables created successfully')

def splitEmailAddresses(emailString):
    '''
    The function splits a comma-separated string of email addresses into a unique list.

    Args:
        emailString: A string containing email addresses separated by commas.

    Returns:
        A list of unique email addresses.
    '''
    if emailString:
        addresses = emailString.split(',')
        uniqueAddresses = list(frozenset(map(lambda x: x.strip(), addresses)))
        return uniqueAddresses
    return []

def parse_email(raw_email):
    # Parse the raw email content
    email_message = email.message_from_string(raw_email, policy=policy.default)
    content_parts = []
    metadata = {}

    for part in email_message.walk():
        content_type = part.get_content_type()
        if content_type == 'text/plain':
            # Handle email body
            content_parts.append(part.get_payload())

    # Extract metadata
    for header in email_message.keys():
        metadata[header] = email_message.get(header)

    content = ''.join(content_parts)

    fromAddresses = splitEmailAddresses(email_message.get("From"))
    toAddresses = splitEmailAddresses(email_message.get("To"))
    ccEmail = splitEmailAddresses(email_message.get("Cc"))
    bccEmail = splitEmailAddresses(email_message.get("Bcc"))
    parsed_email = {
        "message_id": email_message.get("Message-ID"),
        "date": email_message.get("Date"),
        "sender_email": fromAddresses[0],
        "to_emails": toAddresses,
        "cc_emails": ccEmail,
        "bcc_emails": bccEmail,
        "subject": email_message.get("Subject"),
        "content": content,
        "metadata": metadata,
        "file_path": "",  
    }

    return parsed_email

def process_and_sink():
    # Get all emails that have not been processed and sink
    emails = collection.find({"processed": False})
    # Process and sink the emails
    for email_doc in emails:
        raw_email = email_doc.get("message")
        if not raw_email:
            continue

        email_message = email.message_from_string(raw_email, policy=policy.default)
        content_parts = []
        metadata = {}

        for part in email_message.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                content_parts.append(part.get_payload())

        content = ''.join(content_parts)

        # Insert email data into Emails table
        pg_cursor.execute("""
            INSERT INTO Emails (message_id, subject, body, mime_version, content_type, content_transfer, date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            email_message['Message-ID'],
            email_message['Subject'],
            content,
            email_message['MIME-Version'],
            email_message['Content-Type'],
            email_message['Content-Transfer-Encoding'],
            email_message['Date']
        ))
        email_id = pg_cursor.fetchone()[0]

        # Insert user data into Users table
        from_email = email_message['From']
        pg_cursor.execute("""
            INSERT INTO Users (email, name)
            VALUES (%s, %s)
            ON CONFLICT (email) DO NOTHING
            RETURNING id
        """, (from_email, from_email.split('@')[0]))
        user_id_row = pg_cursor.fetchone()
        if user_id_row is None:
            pg_cursor.execute("SELECT id FROM Users WHERE email = %s", (from_email,))
            user_id_row = pg_cursor.fetchone()
        user_id = user_id_row[0]

        # Insert recipient data into Recipients table
        to_emails = email_message.get_all('To', [])
        for to_email in to_emails:
            pg_cursor.execute("""
                INSERT INTO Recipients (email_id, user_id, recipient_type)
                VALUES (%s, %s, %s)
            """, (email_id, user_id, 'to'))

        # Mark email as processed
        collection.update_one({"_id": email_doc["_id"]}, {"$set": {"processed": True}})

    conn.commit()
    print('Emails, users, and recipients processed and sunk successfully')

default_args = {
    'owner': 'TaiDuongDevOps',
    'start_date': datetime.datetime.now() - datetime.timedelta(minutes=1),
    'retries': 1,
    'retry_delay': datetime.timedelta(minutes=5),
}

with DAG(
    'Lab9',
    default_args=default_args,
    description='Lab9 DAG',
    schedule_interval='*/5 * * * *',
    catchup=False,
    tags=['lab9'],
) as dag:
    get_data_task = PythonOperator(
        task_id='get_random_data',
        python_callable=get_random_data,
        op_args=[df],
    )

    insert_data_task = PythonOperator(
        task_id='insert_data',
        python_callable=insert_data,
        op_args=[get_data_task.output],
    )

    create_table_task = PythonOperator(
        task_id='create_table',
        python_callable=create_table,
    )

    process_and_sink_task = PythonOperator(
        task_id='process_and_sink',
        python_callable=process_and_sink,
    )

    get_data_task >> insert_data_task >> create_table_task >> process_and_sink_task
