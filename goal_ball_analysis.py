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