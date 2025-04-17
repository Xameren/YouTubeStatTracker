import requests
import json
import datetime
from flask import Flask, render_template, request, jsonify
import dailyupdater
import os
from dotenv import load_dotenv
app = Flask(__name__)

# TODO list
# - delte all the comments in the script, like brother we can tell what these things do
# - replace JSON files with SQL databases


# without these done, the script still works well, but on a large scale it can take some time to load
# I'll be making these over time, you do not need to do anything.


@app.route("/")
def home():
    return render_template("index_main.html")


load_dotenv()

@app.route("/submit", methods=["POST"])
def main():
    global history_date, history_subscribers, history_videos, history_views, recent_video_thumbnail
    API_KEY = os.getenv("API_KEY")
    CHANNEL_ID = request.form.get('username')
    def getResponse(url):
        try:
            response = requests.get(url) #get stuff from the api
            response.raise_for_status()
            print(response)
            return response
        except Exception as e:
            print("Error:", e)
    if CHANNEL_ID == "" or None:
        return render_template("index_main.html")
    if not CHANNEL_ID.startswith("UC") and len(CHANNEL_ID) != 24: # checks if the user inputed a valid channel ID or not. If not, it searches for it using the youtube API. 
        print("Not a valid ID")
        remove_characters = str.maketrans("", "", " -/*+_:?!\"()\\")

        try:
            print("Trying with JSON")
            with open("resolver.json", "r") as file:
                open_json = json.load(file)
            CHANNEL_ID = open_json[CHANNEL_ID.lower().translate(remove_characters)]
        except KeyError:
            app.logger.debug("a")
            print("JSON empty, searching")
            response = getResponse(f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=channel&q={CHANNEL_ID}&maxResults=1&key={API_KEY}")
            channel_response = response.json()
            
            try:
                write_new_name = { 
                    f"{CHANNEL_ID.lower().translate(remove_characters)}": channel_response["items"][0]["snippet"]["channelId"]
                }

                try:
                    
                    with open("resolver.json", "r") as file:
                        open_json = json.load(file)
                    
                    open_json.update(write_new_name)

                except FileNotFoundError:
                    open_json = write_new_name

                except Exception as e:
                    print("Can't read the json", e)

                try:
                    with open("resolver.json", 'w') as file: # writes the search query and the channel ID into resolver.json so if the same search query happens twice, you dont have to look it up again
                        json.dump(open_json, file, indent=4)

                except Exception as e:
                    print("Can't update the json", e)

                CHANNEL_ID = channel_response["items"][0]["snippet"]["channelId"] # redefines channel ID so the API knows what to show
            except Exception as e:
                print(f"Error: {e}, the channel might not exist")

            print("Searched")

    response = getResponse(f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&id={CHANNEL_ID}&key={API_KEY}")
    if response.status_code == 200:
        channel_details = response.json()

        # defines some statistics that got pulled from the API responses
        view_count = channel_details["items"][0]["statistics"]["viewCount"]
        subscriber_count = channel_details["items"][0]["statistics"]["subscriberCount"]
        video_count = channel_details["items"][0]["statistics"]["videoCount"]
        video_playlist = channel_details["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"] # searches for the "all videos" playlist
        channel_description = channel_details["items"][0]["snippet"]["description"]
        channel_custom_URL = channel_details["items"][0]["snippet"]["customUrl"]
        channel_creation_date = channel_details["items"][0]["snippet"]["publishedAt"][:10]
        channel_profile_picture = channel_details["items"][0]["snippet"]["thumbnails"]["medium"]["url"]
        

        response = getResponse(f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={video_playlist}&maxResults=3&key={API_KEY}") #searches for the videos
        videos_playlist = response.json()

        counter = 0
        video_IDs = []
        video_titles = []

        for i in range(len(response.json()["items"])): # counts the amount of videos up to 2. It starts at 0 because thats how the API is built
            video_titles.append(videos_playlist["items"][counter]["snippet"]["title"]) # checks out the title
            video_IDs.append(videos_playlist["items"][counter]["snippet"]["resourceId"]["videoId"]) # looks for video IDs (for views n likes n comments)
            counter += 1
        Channel_title = videos_playlist["items"][0]["snippet"]["channelTitle"]

        response = getResponse(f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={",".join(video_IDs)}&key={API_KEY}") # looks the videos up
        videos_responses = response.json()

        response = getResponse(f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_IDs[0]}&key={API_KEY}")
        recent_video = response.json()
        counter = 0
        video_views = []
        video_likes = []
        video_comments = []

        for i in range(len(videos_responses["items"])): # retrieves the youtuber's stats for the 3 latest videos    
            video_views.append(videos_responses["items"][counter]["statistics"]["viewCount"])
            video_likes.append(videos_responses["items"][counter]["statistics"]["likeCount"])
            video_comments.append(videos_responses["items"][counter]["statistics"]["commentCount"])
            counter += 1

        recent_video_thumbnail = recent_video["items"][0]["snippet"]["thumbnails"]["medium"]["url"]
        recent_video_title = recent_video["items"][0]["snippet"]["title"]
        recent_video_views = video_views[0]
        recent_video_likes = video_likes[0]
        recent_video_comments = video_comments[0]
        
        history = ""
        history_date = []
        history_subscribers = []
        history_views = []
        history_videos = []
        videos_string = ""

        counter = 0
        today = datetime.datetime.now().strftime("%Y-%m-%d")

        with open("UserTracker.json", "r") as file:
            user_tracker = json.load(file)

        if CHANNEL_ID not in user_tracker:
            dailyupdater.save_user_tracker(CHANNEL_ID, Channel_title, subscriber_count, view_count, video_count) #saves the stats to UserTracker using dailyupdater

        with open("UserTracker.json", "r") as file:
            user_tracker = json.load(file)

        for stat in user_tracker[CHANNEL_ID]["stats"]:
            counter += 1
            history += f"Date: {stat['date']} | Subscribers: {stat['subscribers']} | Views: {stat['views']} | Videos: {stat['videos']}\n"
            history_date.append(stat['date'])
            history_subscribers.append(stat['subscribers'])
            history_views.append(stat['views'])
            history_videos.append(stat['videos'])
            if counter == 30:
                break
        add_todays_date_to_the_charts = True
        
        # this block of code prevents duplicate data points for today's data to be shown in the front end
        try:
            if user_tracker[CHANNEL_ID]["stats"][-1]["date"] == today:
                add_todays_date_to_the_charts = False
        except Exception:
            pass
        
        if add_todays_date_to_the_charts: # in the case of there not being any data on the requested channel, put todays data into the charts
            history += f"Date: {today} | Subscribers: {subscriber_count} | Views: {view_count} | Videos: {video_count}"
            history_date.append(today)
            history_subscribers.append(subscriber_count)
            history_views.append(view_count)
            history_videos.append(video_count)

        for i in range(len(videos_responses["items"])):
                videos_string += f"{video_titles[i]} | {video_views[i]} Views | {video_likes[i]} Likes | {video_comments[i]} Comments |\n"
        
        viewspervideo = "{:,}".format(round(int(view_count)/int(video_count)))
        view_count = "{:,}".format(int(view_count))
        video_count = "{:,}".format(int(video_count))
        subscriber_count = "{:,}".format(int(subscriber_count))
        print(f"""
=================================
Showing details for {Channel_title}
=================================
Custom URL: {channel_custom_URL}
Channel creation date: {channel_creation_date}
Channel profile picture: {channel_profile_picture}
Subscribers: {subscriber_count}  Views: {view_count} Videos: {video_count}

Latest 3 videos:
{videos_string}

Description:
{channel_description}
=================================
History
==================================
No further history was tracked
{history}
""")

    else:
        print("Error:", response.status_code, response.text)
    return render_template("index.html", Channel_title=Channel_title, viewspervideo=viewspervideo, subscriber_count=subscriber_count, view_count=view_count, video_count=video_count, channel_creation_date=channel_creation_date, channel_description = channel_description, channel_profile_picture = channel_profile_picture, channel_custom_URL = channel_custom_URL, recent_video_comments = recent_video_comments, recent_video_likes = recent_video_likes, recent_video_views = recent_video_views, recent_video_title = recent_video_title, recent_video_thumbnail = recent_video_thumbnail)
    # The holy line, do not touch, only add upon it

@app.route("/chart-data")
def chart_data_subs():
    print(f"Type of history_date: {type(history_date)}")
    print(f"Type of history_subscribers: {type(history_subscribers)}")
    print(f"history_date: {history_date}")
    print(f"history_subscribers: {history_subscribers}")
    return jsonify({
        "labels_date": list(history_date),
        "data_subscribers": list(history_subscribers),
        "data_views": list(history_views)
    })

@app.route('/get_recent_video_thumbnail')
def get_recent_video_thumbnail():
    return jsonify({'thumbnail_url': f'{recent_video_thumbnail}'})

if __name__ == "__main__":
    app.run()
