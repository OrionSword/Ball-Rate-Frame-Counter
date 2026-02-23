import cv2
from os import path
import json

print("OpenCV version: " + cv2.__version__)

VIDEO_FOLDER_PATH = "C:\\Users\\orion\\Videos\\2026 Week 0\\"
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
    ]

def video_frame_by_frame(folder_path, filename):
    video_path = folder_path + filename

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return

    cv2.namedWindow("Video Playback", cv2.WINDOW_NORMAL) #, cv2.WINDOW_AUTOSIZE
    cv2.resizeWindow("Video Playback", 1600, 900)
    
    # Start in a paused state to allow frame-by-frame navigation immediately
    # Read the first frame
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame. Exiting...")
        return
    
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Frames: {frame_count}")
    frame_ball_flags = [False for f in range(frame_count)] #list of false flags for each frame
    ball_count = 0

    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"FPS: {fps} frames per second")
    frame_time = 1.0/fps
    print(f"Frame Time: {frame_time} seconds")
    
    current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
    # Add frame number text to the frame
    frame_with_text = add_frame_text(frame, current_frame_pos, ball_count, frame_ball_flags[current_frame_pos])
    cv2.imshow("Video Playback", frame_with_text)
    
    while True:
        # Wait indefinitely for a key press (0ms delay)
        key = cv2.waitKey(0) & 0xFF

        if key == ord('q'):
            # Press 'Q' to quit
            break

        elif key == ord('d'):
            # Press "D" key to go to the next frame
            # The next read() call will advance the frame automatically
            ret, frame = cap.read()
            if not ret:
                print("End of video reached. Looping is not implemented here.")
                continue # Stay on the last frame
            
            current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            frame_with_text = add_frame_text(frame, current_frame_pos, ball_count, frame_ball_flags[current_frame_pos])
            cv2.imshow("Video Playback", frame_with_text)

        elif key == ord('a'):
            # Press "A" key to go to the previous frame
            current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            if current_frame_pos > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_pos - 1) 
                ret, frame = cap.read()
                if ret:
                    current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                    frame_with_text = add_frame_text(frame, current_frame_pos, ball_count, frame_ball_flags[current_frame_pos])
                    cv2.imshow("Video Playback", frame_with_text)
        
        elif key == ord('b'):
            #press "B" key to toggle ball flag for current frame
            current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            ball_count += -1 if frame_ball_flags[current_frame_pos] else 1
            frame_ball_flags[current_frame_pos] = not frame_ball_flags[current_frame_pos] #toggle
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_pos)
            ret, frame = cap.read()
            if ret:
                current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                frame_with_text = add_frame_text(frame, current_frame_pos, ball_count, frame_ball_flags[current_frame_pos])
                cv2.imshow("Video Playback", frame_with_text)


    cap.release()
    cv2.destroyAllWindows()

    return fps, frame_ball_flags

def add_frame_text(frame, frame_num, ball_count, ball_flag):
    """Adds the current frame number as text to the video frame."""
    font = cv2.FONT_HERSHEY_SIMPLEX

    text = f"Frame: {frame_num}"
    cv2.putText(frame, text, (10, 30), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
    text = f"Ball Count: {ball_count}"
    cv2.putText(frame, text, (10, 80), font, 1, (255, 255, 255), 2, cv2.LINE_AA)

    if ball_flag:
        text = f"BALL THIS FRAME"
        cv2.putText(frame, text, (10, 170), font, 3, (43, 225, 254), 2, cv2.LINE_AA)

    return frame

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

    json_data = {}
    video_frames = []

    #Loop through all frames until the video ends
    success, frame = cap.read() #Read the first frame
    while success:
        video_frames.append(frame)
        success, frame = cap.read()
    
    json_data["frame_count"] = len(video_frames)
    json_data["fps"] = cap.get(cv2.CAP_PROP_FPS)
    json_data["match_start_frame"] = 0
    
    # Release the video capture object and destroy all windows
    cap.release()

    if path.isfile(json_path): #file was parsed before, open the existing json data
        with open('data.json', 'r') as file:
            json_data = json.load(file)
    else: #create blank data for the video and save it to a new file
        pass


if __name__ == "__main__":
    
    fps, frame_flags = video_frame_by_frame(VIDEO_FOLDER_PATH, VIDEO_FILENAME)

