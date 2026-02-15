import cv2

print("OpenCV version: " + cv2.__version__)

# Replace 'your_video_file.mp4' with the path to your video file
VIDEO_FILE_PATH = "C:\\Users\\orion\\Videos\\2026 Robot\\20260214_162910.mp4"

def video_frame_by_frame(video_path):
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

def ball_analysis(fps, frame_flags):

    print("\nStarting analysis...")

    frame_time = 1.0/fps
    frame_count = len(frame_flags)
    ball_count = frame_flags.count(True)

    last_flag_frame_number = -1
    gap_times = []

    #count the frame spacing for each "true" flagged frame and calculate time spacing
    for i in range(frame_count):
        frame_flag = frame_flags[i]

        if frame_flag:
            if last_flag_frame_number != -1: #have we detected at least one other ball before (otherwise all this is meaningless)
                gap_frames = i - last_flag_frame_number
                gap_time = frame_time * gap_frames #assumes constant frame rate
                gap_times.append(gap_time)
            last_flag_frame_number = i
    
    #track the cumulative time for groups of balls of sizes ranging from 1 (encoded as 0) to the total number of balls (minus 1)
    shortest_group_times = [1e+10 for x in range(ball_count-1)] #gap timnes will be 1 less than ball count since this is 0-based
    current_group_times = []

    for i in range(ball_count - 1):
        gap_time = gap_times[i]
        if i == 0:
            current_group_times = [gap_time]
        else:
            current_group_times = [g + gap_time for g in current_group_times]
            current_group_times.insert(0, gap_time) #list grows longer as we encounter more balls
        
        for j in range(i+1):
            if current_group_times[j] < shortest_group_times[j]:
                shortest_group_times[j] = current_group_times[j]
    
    #print ball timings
    print("\nBALL GAPS:")
    print("Ball 0:  0.000s (0.0bps)")
    for i in range(len(gap_times)):
        index = i + 1
        gap_time = gap_times[i]
        bps = 1/gap_time
        print(f"Ball {index}:  {gap_time:.3f}s ({bps:.1f}bps)")
    
    #print shortest group times
    print("\nSHORTEST TIME TO LAUNCH N BALLS:")
    for i in range(len(shortest_group_times)):
        group_size = i + 1
        group_time = shortest_group_times[i]
        group_bps = group_size / group_time
        print(f"N={group_size}:  {group_time:.3f}s ({group_bps:.1f}bps)")

    return

if __name__ == "__main__":
    
    fps, frame_flags = video_frame_by_frame(VIDEO_FILE_PATH)

    ball_analysis(fps, frame_flags)

