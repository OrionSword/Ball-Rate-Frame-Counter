import cv2
from os import path
import json
import math
import numpy as np
import threading
import time

print("OpenCV version: " + cv2.__version__)

VIDEO_FOLDER_PATH = "C:\\Users\\odeyoe\\Videos\\2026 Week 0\\Red Hub\\"
VIDEO_FILENAME = "Match 6 Red.mp4"

FRAME_SCALE = 1.0
PREVIEW_SCALE = 0.5

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

class FrameBlock:
    def __init__(self, index, start_frame, end_frame):
        self.block_index = index
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.frames = []
    
    def get_frame(self, frame_index):
        index_in_block = frame_index - self.start_frame
        return self.frames[index_in_block]

class VideoLoader:
    def __init__(self, folder_path, file_name):
        self.folder_path = folder_path
        self.file_name = file_name
        self.path = folder_path + file_name

        #load video and pull some metadata
        self.cap = cv2.VideoCapture(self.path)

        if not self.cap.isOpened():
            raise RuntimeError("Failed to open video.")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.video_length_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        #load first frame
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to read video.")
        self.current_frame_img = cv2.resize(frame, (0, 0), fx=FRAME_SCALE, fy=FRAME_SCALE, interpolation=cv2.INTER_AREA)
        self.current_pos_frames = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        self.frame_height, self.frame_width, _ = self.current_frame_img.shape

        #derived values
        self.block_size = max(1, round(self.fps*5.0))
        self.video_length_blocks = math.ceil(self.video_length_frames / self.block_size)
        self.video_length_seconds = self.video_length_frames / self.fps
        self.current_pos_seconds = self.current_pos_frames / self.fps
        self.current_pos_blocks = self.current_pos_frames // self.block_size

        #caches and important state variables
        self.black_frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        self.previews = None #will be a list
        self.previous_block = None #will be a FrameBlock
        self.current_block = None #will be a FrameBlock
        self.next_block = None #will be a FrameBlock
        self.cap_lock = threading.Lock()
        self.previews_lock = threading.Lock()
        self.previous_block_lock = threading.Lock()
        self.current_block_lock = threading.Lock()
        self.next_block_lock = threading.Lock()
        self.frame_changed_flag = False
        self.need_frame_flag = False
        self.need_block_update_flag = False
        self.blocks_out_of_date_flag = False

        

        self.block_update_thread = threading.Thread(target=self._update_blocks, args=(self.current_pos_blocks, self.blocks_out_of_date_flag))
        self.block_update_thread.start()
        print("Starting block loading...")
        self.block_start_time = time.perf_counter()

        self.previews_thread = threading.Thread(target=self._load_previews)
        self.previews_thread.start()
        print("Starting preview loading...")
        self.preview_start_time = time.perf_counter()

    def __del__(self):
        with self.cap_lock:
            self.cap.release()

    #HIGH LEVEL FUNCTIONS
    def check_for_frame_update(self): #this should be run by the user in the UI loop
        #check on preview loading (only runs once) and report on performance
        if self.previews_thread is not None:
            if not self.previews_thread.is_alive():
                end_time = time.perf_counter()
                print(f"\tPreview loading finished in {end_time-self.preview_start_time:.4f} seconds.")
                self.previews_thread = None
        
        #handle block updates
        if self.block_update_thread is None:
            if self.need_block_update_flag:
                self.block_update_thread = threading.Thread(target=self._update_blocks, args=(self.current_pos_blocks, self.need_block_update_flag))
                self.block_update_thread.start()
                self.block_start_time = time.perf_counter()
                self.need_block_update_flag = False
        elif not self.block_update_thread.is_alive():
            end_time = time.perf_counter()
            print(f"\tBlock update took {end_time-self.block_start_time:.4f} seconds.")
            self.block_update_thread.join() #I don't think this is actually necessary, but it should be very fast
            self.block_update_thread = None
            if not self.need_block_update_flag: #this is to handle situations where a block update is called for while one is already running (a relatively likely scenario while scrubbing)
                self.blocks_out_of_date_flag = False
        
        #handle deferred image updates
        if self.need_frame_flag:
            if (not self.blocks_out_of_date_flag) and (self._current_block_available()):
                with self.current_block_lock:
                    self.current_frame_img = self.current_block.get_frame(self.current_pos_frames)
                self.frame_changed_flag = True
            else: #fall back on previews here (might get rid of this if they're annoying)
                if self._previews_available():
                    with self.previews_lock:
                        preview_frame = self.previews[self.current_pos_blocks]
                    reverse_scale = FRAME_SCALE/PREVIEW_SCALE
                    self.current_frame_img = cv2.resize(preview_frame, (0, 0), fx=reverse_scale, fy=reverse_scale, interpolation=cv2.INTER_AREA) #hopefully this resize is fast enough?  If not we'll have to store full size previews
                    self.frame_changed_flag = True
                    #leave "need_frame_flag" true
        
        #pass the current frame to the user with a signal if it changed
        if self.frame_changed_flag:
            self.frame_changed_flag = False
            return True, self.current_frame_img
        else:
            return False, self.current_frame_img

    def jump_to_frame_with_preview(self, frame_index):
        #clamp the frame index between acceptable limits
        frame_index = max(0, min(frame_index, self.video_length_frames - 1))

        #check if the jump is within the already-loaded blocks
        if self._move_to_frame_in_blocks(frame_index):
            return
        else:
            #kick off a block update if we aren't jumping to the same block we're already in
            if self._block_index_from_frame(frame_index) != self.current_pos_blocks:
                self.need_block_update_flag = True
                self.blocks_out_of_date_flag = True

        #don't even bother trying to load directly from the cap, random reads are too slow
        #move on to loading a preview image if one exists
        if self._previews_available():
            with self.previews_lock:
                self._update_position(frame_index)
                preview_frame = self.previews[self.current_pos_blocks]
                reverse_scale = FRAME_SCALE/PREVIEW_SCALE
                self.current_frame_img = cv2.resize(preview_frame, (0, 0), fx=reverse_scale, fy=reverse_scale, interpolation=cv2.INTER_AREA) #hopefully this resize is fast enough?  If not we'll have to store full size previews
                self.frame_changed_flag = True
                self.need_frame_flag = True
                return

        #fall back to a black frame if needed
        self._update_position(frame_index)
        self.current_frame_img = self.black_frame
        self.frame_changed_flag = True
        self.need_frame_flag = True
        return

    def next_frame(self):
        if self.current_pos_frames < (self.video_length_frames - 1):
            if self._move_to_frame_in_blocks(self.current_pos_frames + 1):
                return

            if self._cap_available(): #I don't expect that this will be true very often if the program reaches this step because the background thread is almost certainly using "cap"
                with self.cap_lock:
                    ret, frame = self.cap.read() #this should be fast enough that we can do this live and block the main thread
                    self.current_frame_img = cv2.resize(frame, (0, 0), fx=FRAME_SCALE, fy=FRAME_SCALE, interpolation=cv2.INTER_AREA)
                    self.frame_changed_flag = True
                    return
            else:
                self.current_frame_img = self.black_frame
                self.frame_changed_flag = True
                self.need_frame_flag = True
                return

    def previous_frame(self):
        if self.current_pos_frames > 0:
            if self._move_to_frame_in_blocks(self.current_pos_frames - 1):
                return

            #going backwards on the capture is so slow that it's not ever worth trying, just give a black frame and move on
            self.current_frame_img = self.black_frame
            self.frame_changed_flag = True
            self.need_frame_flag = True
            return

    #ASYNCHRONOUS FUNCTIONS
    def _load_previews(self):
        time.sleep(0.5)
        with self.previews_lock:
            self.previews = []
            with self.cap_lock:
                old_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                for i in range(self.video_length_blocks):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, i * self.block_size)
                    ret, frame = self.cap.read()
                    self.previews.append(cv2.resize(frame, (0, 0), fx=PREVIEW_SCALE, fy=PREVIEW_SCALE, interpolation=cv2.INTER_AREA)) #skipping "if ret:" so this throws an error if it doesn't get a frame for some reason
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, old_pos) #clean up cap after ourselves
        
        return
    
    def _update_blocks(self, block_index, out_of_date_flag):
        #start by locking all blocks and checking if any shifts are needed
        if out_of_date_flag:
            with self.previous_block_lock, self.current_block_lock, self.next_block_lock:
                if self.current_block is not None: #shouldn't be able to get into this state but doing a check anyways
                    #only referencing "current_block" here because next and previous can be up against the ends of the video and be None and then we can't check their index
                    if block_index == self.current_block.block_index + 1: #shift backward
                        self.previous_block = self.current_block
                        self.current_block = self.next_block
                        self.next_block = None #next step will populate this
                    elif block_index == self.current_block.block_index - 1: #shift forward
                        self.next_block = self.current_block
                        self.current_block = self.previous_block
                        self.previous_block = None #next step will populate this
                    elif abs(block_index - self.current_block.block_index) == 2: #edge case after a jump where there is still some overlap and we can salvage one of the blocks
                        self.current_block = None
                        if block_index < self.current_block.block_index:
                            self.next_block = self.previous_block
                            self.previous_block = None
                        else:
                            self.previous_block = self.next_block
                            self.next_block = None
                    elif block_index != self.current_block.block_index: #we made a big jump, throw everything out (this function shouldn't ever be called if these condition values are the same, but just making sure)
                        self.previous_block = None
                        self.current_block = None
                        self.next_block = None
        
        #do a second pass one-by-one checking for empty blocks that need filled (doing this so that only 1 block is locked at a time while loading new frames)
        with self.current_block_lock:
            if self.current_block is None:
                self.current_block = self._load_block(block_index)
        
        if (block_index < self.video_length_blocks - 1):
            with self.next_block_lock:
                if self.next_block is None:
                    self.next_block = self._load_block(block_index + 1)

        if (block_index > 0):
            with self.previous_block_lock:
                if self.previous_block is None:
                    self.previous_block = self._load_block(block_index - 1)
        
        return

    def _load_block(self, block_index):
        block_start = self._block_start_frame(block_index)
        block_end = self._block_end_frame(block_index)
        block_length = block_end - block_start + 1

        block = FrameBlock(block_index, block_start, block_end)
        with self.cap_lock:
            old_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, block_start)
            for _ in range(block_length):
                ret, frame = self.cap.read()
                block.frames.append(cv2.resize(frame, (0, 0), fx=FRAME_SCALE, fy=FRAME_SCALE, interpolation=cv2.INTER_AREA)) #skipping "if ret:" so this throws an error if it doesn't get a frame for some reason
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, old_pos) #clean up cap after ourselves
        
        return block
    
    def _cap_available(self):
        return not self.cap_lock.locked()
    
    def _previews_available(self):
        return (not self.previews_lock.locked()) and (self.previews is not None)
    
    def _previous_block_available(self):
        return (not self.previous_block_lock.locked()) and (self.previous_block is not None)
    
    def _current_block_available(self):
        return (not self.current_block_lock.locked()) and (self.current_block is not None)
    
    def _next_block_available(self):
        return (not self.next_block_lock.locked()) and (self.next_block is not None)
    
    #INTERNAL FUNCTIONS
    def _update_position(self, frame_index):
        self.current_pos_frames = frame_index
        self.current_pos_seconds = self.current_pos_frames / self.fps
        self.current_pos_blocks = self.current_pos_frames // self.block_size
    
    def _move_to_frame_in_blocks(self, frame_index):
        if not self.blocks_out_of_date_flag: #make sure blocks aren't out of date
            target_block_index = self._block_index_from_frame(frame_index)
            if target_block_index == self.current_pos_blocks:
                if self._current_block_available():
                    with self.current_block_lock:
                        self._update_position(frame_index)
                        self.current_frame_img = self.current_block.get_frame(self.current_pos_frames)
                    self.frame_changed_flag = True
                    #don't need a block update here because we stayed in the same block
                    return True
            elif target_block_index == (self.current_pos_blocks - 1):
                if self._previous_block_available():
                    with self.previous_block_lock:
                        self._update_position(frame_index)
                        self.current_frame_img = self.previous_block.get_frame(self.current_pos_frames)
                    self.frame_changed_flag = True
                    self.need_block_update_flag = True
                    self.blocks_out_of_date_flag = True
                    return True
            
            elif target_block_index == (self.current_pos_blocks + 1):
                if self._next_block_available():
                    with self.next_block_lock:
                        self._update_position(frame_index)
                        self.current_frame_img = self.next_block.get_frame(self.current_pos_frames)
                    self.frame_changed_flag = True
                    self.need_block_update_flag = True
                    self.blocks_out_of_date_flag = True
                    return True
        
        return False

    #HELPER FUNCTIONS
    def _block_index_from_frame(self, frame_index):
        return frame_index // self.block_size
    
    def _block_start_frame(self, block_index):
        return block_index * self.block_size
    
    def _block_end_frame(self, block_index):
        return min(self.video_length_frames - 1, self._block_start_frame(block_index) + self.block_size - 1)


def video_frame_by_frame(folder_path, filename):
    loader = VideoLoader(folder_path, filename)
    json_data = open_and_parse_json(folder_path, filename, loader)
    
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

    current_frame_img = loader.current_frame_img
    gui_update = True

    frame_with_text = add_frame_text(current_frame_img, json_data, loader.current_pos_frames, current_alliance, current_mode, current_ball_group_name)
    cv2.imshow("Video Playback", frame_with_text)
    
    while True:
        # Wait indefinitely for a key press (0ms delay)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'): #QUIT
            break

        elif key == ord('m'): #NEXT FRAME
            loader.next_frame()

        elif key == ord('n'): #PREVIOUS FRAME
            loader.previous_frame()
        
        elif key == ord('p'): #FORWARD ~5sec
            loader.jump_to_frame_with_preview(loader.current_pos_frames + int(loader.fps * 5.0))

        elif key == ord('o'): #BACKWARD ~5sec
            loader.jump_to_frame_with_preview(loader.current_pos_frames - int(loader.fps * 5.0))

        elif key == ord('b'): #TOGGLE ALLIANCE
            if current_alliance == "red_alliance":
                current_alliance = "blue_alliance"
            else:
                current_alliance = "red_alliance"
            gui_update = True
        
        elif key == ord('v'): #TOGGLE MODE
            if current_mode == "balls_entering":
                current_mode = "balls_leaving"
            else:
                current_mode = "balls_entering"
            gui_update = True
        
        elif key == ord('t'): #MOVE MATCH START HERE
            json_data["match_start_frame"] = loader.current_pos_frames
            gui_update = True

        elif key == ord('s'): #SWITCH TO NEXT BALL GROUP
            current_ball_group_num = (current_ball_group_num + 1) % len(BALL_GROUP_NAMES) #wrap around
            current_ball_group_name = BALL_GROUP_NAMES[current_ball_group_num]
            gui_update = True
        
        elif key == ord('w'): #SWITCH TO PREVIOUS BALL GROUP
            current_ball_group_num = (current_ball_group_num - 1) % len(BALL_GROUP_NAMES) #wrap around
            current_ball_group_name = BALL_GROUP_NAMES[current_ball_group_num]
            gui_update = True
        
        elif key == ord('d'): #INCREASE BALL COUNT
            new_count = json_data["frame_data"][loader.current_pos_frames][current_alliance][current_mode][current_ball_group_name] + 1
            json_data["frame_data"][loader.current_pos_frames][current_alliance][current_mode][current_ball_group_name] = new_count
            gui_update = True
        
        elif key == ord('a'): #DECREASE BALL COUNT
            new_count = json_data["frame_data"][loader.current_pos_frames][current_alliance][current_mode][current_ball_group_name] - 1
            if new_count >= 0:
                json_data["frame_data"][loader.current_pos_frames][current_alliance][current_mode][current_ball_group_name] = new_count
            gui_update = True
        
        loader_update, new_frame = loader.check_for_frame_update()
        if loader_update:
            current_frame_img = new_frame

        if loader_update or gui_update:
            frame_with_text = add_frame_text(current_frame_img, json_data, loader.current_pos_frames, current_alliance, current_mode, current_ball_group_name)
            cv2.imshow("Video Playback", frame_with_text)

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

    frame_copy = frame.copy()

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

def open_and_parse_json(folder_path, filename, video_loader):
    json_path = folder_path + json_filename_from_video(filename)
    
    frame_count = video_loader.video_length_frames

    json_data = {}

    json_data["frame_count"] = frame_count

    fps = video_loader.fps
    json_data["fps"] = fps
    json_data["match_start_frame"] = 0
    frame_height = video_loader.frame_height
    frame_width = video_loader.frame_width
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
    
    return json_data


if __name__ == "__main__":
    new_json_data = video_frame_by_frame(VIDEO_FOLDER_PATH, VIDEO_FILENAME)

    json_path = VIDEO_FOLDER_PATH + json_filename_from_video(VIDEO_FILENAME)
    with open(json_path, 'w') as json_file:
        json.dump(new_json_data, json_file, indent=4)

