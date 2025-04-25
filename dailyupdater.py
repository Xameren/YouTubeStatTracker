import requests
import json
import datetime
import time
import os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("API_KEY")

def getResponse(url):
    try:
        response = requests.get(url) #get stuff from the api
        return response
    except Exception as e:
        print("Error:", e)

with open("Resolver.json", "r") as file:
    resolver = json.load(file)
try:
    with open("UserTracker.json", "r") as file:
        user_tracker = json.load(file)
except (FileNotFoundError, json.decoder.JSONDecodeError):
    user_tracker = {}
    print("WARN - Couldnt open UserTracker, assuming an empty list")

def save_user_tracker(channel_id, channel_name, subscribers, views, videos):
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    if channel_id not in user_tracker:
        user_tracker[channel_id] = {"channel_name": channel_name, "stats": []}
    
    user_tracker[channel_id]["stats"].append({
        "date": today,
        "subscribers": subscribers,
        "views": views,
        "videos": videos
    })
    
    with open("UserTracker.json", "w") as file:
        json.dump(user_tracker, file, indent=4)

    print(f"Data written! {channel_name} or {channel_id} | {today} {subscribers} {views} {videos}")

def get_stats(statistic):
    try:
        return channel_statistics["items"][0]["statistics"][statistic]
    except KeyError:
        try:
            print(f"ERROR - FAIL while asigning {statistic.replace("Count", "s")} | Writing the previous value. Reason: Keyerror | API Response: \n {channel_statistics} \n ")
            return user_tracker[channel_id]["stats"][-1][statistic.replace("Count", "s")] # The .replace is there because of the difference between how the API and the UserTracker store stats
        except Exception as ex:
            print(f"ERROR - FAIL while assigning {statistic.replace("Count", "s")} | Writing a 0 \n {channel_statistics} . Reason: {ex}\n ")
            return 0
            


if __name__ == "__main__":

    list_of_people = []

    for username, channel_id in resolver.items():
        list_of_people.append(channel_id)
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        write = True
        
        try:
            if user_tracker[channel_id]["stats"][-1]["date"] == today:
                print("Duplicate detected, not writing")
                write = False
        except Exception as e:
            print("Duplicate check failed, user might be missing. ", e)
        if write:
            save_user = True
            response = getResponse(f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={API_KEY}")
            channel_statistics = response.json()
            try:
                view_count = get_stats("viewCount")
                subscriber_count = get_stats("subscriberCount")
                video_count = get_stats("videoCount")
            except KeyError:
                print(f"ERROR - API response invalid. Response: {response} {channel_statistics}")
                save_user = False

            time.sleep(0.5)
            
            if save_user:
                save_user_tracker(channel_id, username, subscriber_count, view_count, video_count)  # ID, username, subscribers, views, videos
