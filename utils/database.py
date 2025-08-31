# Add or update user in DB
def add_user(user_id, username):
    users_collection.update_one(
        {"user_id": user_id},  # filter
        {"$set": {"username": username}},  # data to set
        upsert=True
    )

# Get user from DB
def get_user(user_id):
    return users_collection.find_one({"user_id": user_id})
