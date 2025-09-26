from pymongo import MongoClient, ASCENDING, DESCENDING
from config import Config

client = MongoClient(Config.MONGODB_URI)
db = client[Config.MONGODB_DB]

users = db["users"]
transactions = db["transactions"]

users.create_index("email", unique=True)
transactions.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
transactions.create_index([("user_id", ASCENDING), ("category", ASCENDING)])
transactions.create_index([("user_id", ASCENDING), ("description", ASCENDING)])
