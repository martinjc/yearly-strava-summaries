import os
import time
import json
import logging
from dotenv import load_dotenv
from stravalib.client import Client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from parent directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# Define paths relative to this script
SCRIPT_DIR = os.path.dirname(__file__)
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'strava_tokens.json')
# Data is in ../data/activities.json
ACTIVITIES_FILE = os.path.join(os.path.dirname(SCRIPT_DIR), 'data', 'activities.json')

CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')

def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        logging.error(f"{TOKEN_FILE} not found. Please run authenticate.py first.")
        return None
    
    with open(TOKEN_FILE, 'r') as f:
        return json.load(f)

def save_tokens(tokens):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=4)
    logging.info(f"Tokens updated and saved to {TOKEN_FILE}")

def get_client():
    tokens = load_tokens()
    if not tokens:
        return None
    
    client = Client()
    client.access_token = tokens['access_token']
    client.refresh_token = tokens['refresh_token']
    client.token_expires_at = tokens['expires_at']
    
    # Check if token is expired (or close to expiring, e.g., within 5 minutes)
    if time.time() > tokens['expires_at'] - 300:
        logging.info("Access token expired or expiring soon. Refreshing...")
        try:
            refresh_response = client.refresh_access_token(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                refresh_token=tokens['refresh_token']
            )
            
            # Update tokens
            tokens['access_token'] = refresh_response['access_token']
            tokens['refresh_token'] = refresh_response['refresh_token']
            tokens['expires_at'] = refresh_response['expires_at']
            
            save_tokens(tokens)
            
            # Update client with new token
            client.access_token = tokens['access_token']
            client.refresh_token = tokens['refresh_token']
            client.token_expires_at = tokens['expires_at']
            
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            return None
            
    return client

def load_cached_activities():
    if not os.path.exists(ACTIVITIES_FILE):
        return []
    try:
        with open(ACTIVITIES_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        logging.warning("Activity cache file is corrupted or empty. Starting fresh.")
        return []

def save_activities(activities):
    # Ensure activities are sorted by start_date
    activities.sort(key=lambda x: x.get('start_date', ''))
    with open(ACTIVITIES_FILE, 'w') as f:
        json.dump(activities, f, indent=4)
    logging.info(f"Saved {len(activities)} activities to {ACTIVITIES_FILE}")

def download_activities(limit=None):
    client = get_client()
    if not client:
        return

    cached_activities = load_cached_activities()
    
    # Determine the latest activity we have
    after = None
    if cached_activities:
        # Sort just in case the file wasn't sorted
        cached_activities.sort(key=lambda x: x.get('start_date', ''))
        latest_activity = cached_activities[-1]
        after = latest_activity.get('start_date')
        if after:
             logging.info(f"Checking for activities after {after}...")
    
    if not after:
        logging.info("No cached activities found. Downloading all (or up to limit)...")
    
    new_activities = []
    try:
        # Fetch activities
        # Note: get_activities yields Strava model objects. We need to serialize them.
        # Use a higher limit if downloading everything, or the provided limit.
        activity_generator = client.get_activities(after=after, limit=limit)
        
        for activity in activity_generator:
            # Serialize the activity object using model_dump (pydantic v2) or dict()
            # Stravalib 2.0+ uses Pydantic.
            try:
                activity_data = activity.model_dump(mode='json')
            except AttributeError:
                # Fallback for older versions or if model_dump isn't available behaving as expected
                # But based on the install log we have stravalib 2.4 and pydantic 2.x
                activity_data = activity.dict()

            logging.info(f"Fetched new activity: {activity_data.get('name')} ({activity_data.get('start_date')})")
            new_activities.append(activity_data)
            
        logging.info(f"Downloaded {len(new_activities)} new activities.")
        
        if new_activities:
            # Initialize a dict to deduplicate by id
            activity_map = {a['id']: a for a in cached_activities}
            
            # Update/Add new activities
            for a in new_activities:
                activity_map[a['id']] = a
            
            # Convert back to list
            all_activities = list(activity_map.values())
            
            save_activities(all_activities)
        else:
            logging.info("No new activities to save.")

    except Exception as e:
        logging.error(f"Error fetching activities: {e}")
        # Even if we crash, save what we got if anything? 
        # Better to not save partial corrupted state unless we are sure.

if __name__ == "__main__":
    download_activities()
