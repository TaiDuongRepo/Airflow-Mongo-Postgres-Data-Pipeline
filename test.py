from pymongo import MongoClient
import pandas as pd
import random

def get_random_data():
    file_path = '../data/email.csv'
    data = pd.read_csv(file_path)
    # Randomly select 200 rows
    data = data.sample(n=200)
    return data

def insert_data(data):
    client = MongoClient('mongodb://localhost:27017/')
    db = client['test']
    collection = db['email']
    data.reset_index(inplace=True)
    data_dict = data.to_dict("records")
    # check if data already exists in the collection and update it
    for i in data_dict:
        collection.update_one({'email':i['email']}, {"$set": i}, upsert=True)
    print('Data inserted successfully')
