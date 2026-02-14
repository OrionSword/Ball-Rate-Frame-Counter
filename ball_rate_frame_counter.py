import cv2

print(cv2.__version__)

# Replace 'your_video_file.mp4' with the path to your video file
VIDEO_FILE_PATH = "C:\\Users\\orion\\Videos\\2026 Robot\\20260214_162910.mp4"

def video_frame_by_frame(video_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return

    cv2.namedWindow("Video Playback", cv2.WINDOW_AUTOSIZE)
    
    # Start in a paused state to allow frame-by-frame navigation immediately
    # Read the first frame
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame. Exiting...")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"FPS: {fps} frames per second")
    
    current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    # Add frame number text to the frame
    frame_with_text = add_frame_number(frame, current_frame_pos)
    cv2.imshow("Video Playback", frame_with_text)
    
    while True:
        # Wait indefinitely for a key press (0ms delay)
        key = cv2.waitKey(0) & 0xFF

        if key == ord('q'):
            # Press 'q' to quit
            break
        elif key == ord('d'):#key == 83 or key == 2555904: # Right arrow key (Windows)
            # Press right arrow key to go to the next frame
            # The next read() call will advance the frame automatically
            ret, frame = cap.read()
            if not ret:
                print("End of video reached. Looping is not implemented here.")
                continue # Stay on the last frame
            
            current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            frame_with_text = add_frame_number(frame, current_frame_pos)
            cv2.imshow("Video Playback", frame_with_text)

        elif key == ord('a'):#key == 81 or key == 2424832: # Left arrow key (Windows)
            # Press left arrow key to go to the previous frame
            current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            if current_frame_pos > 1:
                # Set the position to 2 frames back because the previous read() already moved us forward once
                cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_pos - 2) 
                ret, frame = cap.read()
                if ret:
                    current_frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                    frame_with_text = add_frame_number(frame, current_frame_pos)
                    cv2.imshow("Video Playback", frame_with_text)
        
        # Note: Key codes for arrow keys may differ across operating systems. 
        # 83 (right) and 81 (left) are common for Windows.
        # For Linux/macOS, you might need different values (e.g., 65363 and 65361).

    cap.release()
    cv2.destroyAllWindows()

def add_frame_number(frame, frame_num):
    """Adds the current frame number as text to the video frame."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = f"Frame: {frame_num}"
    # Put text on the frame using the cv2.putText function
    cv2.putText(frame, text, (10, 30), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
    return frame

if __name__ == "__main__":
    
    video_frame_by_frame(VIDEO_FILE_PATH)

