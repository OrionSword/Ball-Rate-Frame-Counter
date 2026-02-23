import cv2
from os import path
import json

print("OpenCV version: " + cv2.__version__)

VIDEO_FOLDER_PATH = "C:\\Users\\odeyoe\\Videos\\2026 Week 0\\"
VIDEO_FILENAME = "20260221_101139.mp4"

BALL_GROUP_NAMES = [
        "Fuel, Standard",
        "Fuel, Striped Black",
        "Fuel, Striped Green",
        "Fuel, Striped Red",
        "Fuel, Dots Black",
        "Fuel, Dots Green",
        "Fuel, Dots Red",
        "Fuel, Circles Black",
        "Fuel, Circles Green",
        "Fuel, Circles Red",
        "Fuel, Quarters Black",
        "Fuel, Quarters Green",
        "Fuel, Quarters Red",
        "Fuel, Black Dots with Green",
        "Fuel, Black Dots with Red",
        "Fuel, Unknown Marking",
    ]

def video_frame_by_frame(cap, json_data):
    
    cv2.namedWindow("Video Playback", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Video Playback", 1920, 1080)
    
    frame_count = json_data["frame_count"]
    print(f"Frames: {frame_count}")

    fps = json_data["fps"]
    print(f"FPS: {fps} frames per second")
    frame_time = 1.0/fps
    print(f"Frame Time: {frame_time} seconds")
    
    current_alliance = "red_alliance"
    current_mode = "balls_entering"
    current_ball_group_num = 0
    current_ball_group_name = BALL_GROUP_NAMES[current_ball_group_num]

    ret, frame = cap.read()
    current_frame_img = frame
    current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1

    frame_with_text = add_frame_text(current_frame_img, json_data, current_frame_pos, current_alliance, current_mode, current_ball_group_name)
    cv2.imshow("Video Playback", frame_with_text)
    
    while True:
        # Wait indefinitely for a key press (0ms delay)
        key = cv2.waitKey(0) & 0xFF

        if key == ord('q'): #QUIT
            break

        elif key == ord('m'): #NEXT FRAME
            ret, frame = cap.read()
            if ret:
                current_frame_img = frame
                current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1

        elif key == ord('n'): #PREVIOUS FRAME
            if current_frame_pos > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_pos - 1) 
                ret, frame = cap.read()
                if ret:
                    current_frame_img = frame
                    current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        
        elif key == ord('b'): #TOGGLE ALLIANCE
            if current_alliance == "red_alliance":
                current_alliance = "blue_alliance"
            else:
                current_alliance = "red_alliance"
        
        elif key == ord('v'): #TOGGLE MODE
            if current_mode == "balls_entering":
                current_mode = "balls_leaving"
            else:
                current_mode = "balls_entering"
        
        elif key == ord('t'): #MOVE MATCH START HERE
            json_data["match_start_frame"] = current_frame_pos

        elif key == ord('s'): #SWITCH TO NEXT BALL GROUP
            current_ball_group_num = (current_ball_group_num + 1) % len(BALL_GROUP_NAMES) #wrap around
            current_ball_group_name = BALL_GROUP_NAMES[current_ball_group_num]
        
        elif key == ord('w'): #SWITCH TO PREVIOUS BALL GROUP
            current_ball_group_num = (current_ball_group_num - 1) % len(BALL_GROUP_NAMES) #wrap around
            current_ball_group_name = BALL_GROUP_NAMES[current_ball_group_num]
        
        elif key == ord('d'): #INCREASE BALL COUNT
            new_count = json_data["frame_data"][current_frame_pos][current_alliance][current_mode][current_ball_group_name] + 1
            json_data["frame_data"][current_frame_pos][current_alliance][current_mode][current_ball_group_name] = new_count
        
        elif key == ord('a'): #DECREASE BALL COUNT
            new_count = json_data["frame_data"][current_frame_pos][current_alliance][current_mode][current_ball_group_name] - 1
            if new_count >= 0:
                json_data["frame_data"][current_frame_pos][current_alliance][current_mode][current_ball_group_name] = new_count

        if key != 255:
            frame_with_text = add_frame_text(current_frame_img, json_data, current_frame_pos, current_alliance, current_mode, current_ball_group_name)
            cv2.imshow("Video Playback", frame_with_text)

    cap.release()
    cv2.destroyAllWindows()

    return json_data

def add_frame_text(frame, json_data, frame_num, alliance, mode, ball_group_name):
    """Adds an overlay to a frame with information about the current state."""
    frame_time = 1.0 / json_data["fps"]
    match_start_frame = json_data["match_start_frame"]
    current_time = (frame_num - match_start_frame) * frame_time

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    start_offset = 40
    row_height = 50

    frame_copy = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA) #frame.copy()

    text = f"Frame: {frame_num}/{json_data["frame_count"]} [m/n]"
    cv2.putText(frame_copy, text, (10, start_offset + 0 * row_height), font, font_scale, (255, 255, 255), 2, cv2.LINE_AA)

    text = f"Estimated Match Time: {current_time:.2f}s [t]"
    cv2.putText(frame_copy, text, (10, start_offset + 1 * row_height), font, font_scale, (255, 255, 255), 2, cv2.LINE_AA)

    text = "Alliance: Red [b]" if alliance == "red_alliance" else "Alliance: Blue [b]"
    color = (0,0,255) if alliance == "red_alliance" else (255,0,0)
    cv2.putText(frame_copy, text, (10, start_offset + 2 * row_height), font, font_scale, color, 2, cv2.LINE_AA)

    text = "Mode: Balls Entering [v]" if mode == "balls_entering" else "Mode: Balls Leaving [v]"
    color = (0,255,0) if mode == "balls_entering" else (0,255,255)
    cv2.putText(frame_copy, text, (10, start_offset + 3 * row_height), font, font_scale, color, 2, cv2.LINE_AA)

    for i in range(len(BALL_GROUP_NAMES)):
        curr_group_name = BALL_GROUP_NAMES[i]
        curr_ball_data = json_data["frame_data"][frame_num][alliance][mode]

        row = 5 + i
        text = f"{curr_ball_data[curr_group_name]} - " + curr_group_name
        color = (0,255,255) if curr_group_name == ball_group_name else (255,255,255)
        cv2.putText(frame_copy, text, (10, start_offset + row * row_height), font, font_scale, color, 2, cv2.LINE_AA)

    return frame_copy

def json_filename_from_video(filename):
    segments = filename.split(".")
    if (len(segments) != 2):
        raise Exception("The name of the file is invalid and can't be parsed.  It should only have a single period with a valid name and file extension.")
    
    return segments[0] + ".json"

def open_and_parse_files(folder_path, filename):
    video_path = folder_path + filename
    json_path = folder_path + json_filename_from_video(filename)

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return
    
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    json_data = {}
    video_frames = []

    #Loop through all frames until the video ends
    success, frame = cap.read() #Read the first frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    """print("Loading frames...")
    count = 0
    while success:
        updateString = "\t\tLoading frame "+str(count)+"/"+str(frame_count)+"..."
        print(updateString.ljust(40," "),end="\r")

        #small_frame = cv2.resize(frame, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
        video_frames.append(frame)

        success, frame = cap.read()
        count += 1
    
    #frame_count = len(video_frames)
    updateString = "\t\tLoaded "+str(frame_count)+" frames."
    print(updateString.ljust(40," "))"""

    json_data["frame_count"] = frame_count

    fps = cap.get(cv2.CAP_PROP_FPS)
    json_data["fps"] = fps
    json_data["match_start_frame"] = 0
    frame_height, frame_width, _ = frame.shape
    json_data["frame_width"] = frame_width
    json_data["frame_height"] = frame_height

    if path.isfile(json_path): #file was parsed before, open the existing json data
        with open(json_path, 'r') as file:
            json_data = json.load(file)
    else: #create blank data for the video and save it to a new file
        blank_ball_data = {x : 0 for x in BALL_GROUP_NAMES}
        blank_frame_list = [
            {
                "red_alliance" : {"balls_entering" : blank_ball_data.copy(), "balls_leaving" : blank_ball_data.copy()},
                "blue_alliance" : {"balls_entering" : blank_ball_data.copy(), "balls_leaving" : blank_ball_data.copy()}
            }
            for x in range(frame_count)]
        json_data["frame_data"] = blank_frame_list

        with open(json_path, 'w') as json_file:
            json.dump(json_data, json_file, indent=4)
    
    # Release the video capture object and destroy all windows
    #cap.release()
    
    return cap, json_data #video_frames, json_data


if __name__ == "__main__":
    cap, json_data = open_and_parse_files(VIDEO_FOLDER_PATH, VIDEO_FILENAME)
    new_json_data = video_frame_by_frame(cap, json_data)

    json_path = VIDEO_FOLDER_PATH + json_filename_from_video(VIDEO_FILENAME)
    with open(json_path, 'w') as json_file:
        json.dump(new_json_data, json_file, indent=4)

