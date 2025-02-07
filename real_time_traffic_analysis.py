import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

# Load the YOLOv8 model
model = YOLO('models/best.pt')

# Initialize Deep SORT tracker
tracker = DeepSort(max_age=30)

# Define the threshold for traffic classification
heavy_traffic_threshold = 10
moderate_traffic_threshold = 5

# Open the video
cap = cv2.VideoCapture('sample_video.mp4')
frame_number = 0

# Prepare CSV output
csv_data = []
object_movement = {}
entry_exit_log = {}

# Define regions of interest (ROI)
left_region = 400
right_region = 800
exit_region = 1000  # Define exit region

# Process video frames
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame_number += 1
    detection_frame = frame.copy()
    results = model.predict(detection_frame, imgsz=640, conf=0.4)
    detections = []

    # Extract bounding boxes
    for box in results[0].boxes.xyxy:
        x1, y1, x2, y2 = map(int, box[:4])
        detections.append(([x1, y1, x2, y2], 1, 0.9))  # Format: (bbox, class, confidence)

    # Update tracker
    tracked_objects = tracker.update_tracks(detections, frame=frame)
    object_count = len(tracked_objects)

    # Traffic classification
    if object_count > heavy_traffic_threshold:
        traffic_status = 'Heavy Traffic'
    elif object_count > moderate_traffic_threshold:
        traffic_status = 'Moderate Traffic'
    else:
        traffic_status = 'Light Traffic'
    
    # Vehicle count per region
    left_lane_count = 0
    right_lane_count = 0

    # Draw bounding boxes and track paths
    for track in tracked_objects:
        if not track.is_confirmed():
            continue
        x1, y1, x2, y2 = map(int, track.to_tlbr())
        obj_id = track.track_id
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f'ID: {obj_id}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Assign objects to regions
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2

        # Track movement direction
        prev_position = object_movement.get(obj_id, (center_x, center_y))
        movement_direction = 'Left' if center_x < prev_position[0] else 'Right'
        object_movement[obj_id] = (center_x, center_y)
        
        if center_x < left_region:
            left_lane_count += 1
        elif center_x > right_region:
            right_lane_count += 1
        
        # Entry/Exit Logging
        if obj_id not in entry_exit_log and center_x < right_region:
            entry_exit_log[obj_id] = 'Entered'
        elif obj_id in entry_exit_log and center_x > exit_region:
            entry_exit_log[obj_id] = 'Exited'
        
        entry_status = entry_exit_log.get(obj_id, 'In Zone')
        
        # Append data for CSV output
        csv_data.append([frame_number, obj_id, 'Vehicle', traffic_status, movement_direction, entry_status])

    # Display traffic status
    cv2.putText(frame, f'Traffic: {traffic_status}', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(frame, f'Left Lane: {left_lane_count}', (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    cv2.putText(frame, f'Right Lane: {right_lane_count}', (50, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    cv2.imshow('Traffic Analysis', frame)

    # Exit on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Save CSV file
csv_df = pd.DataFrame(csv_data, columns=['Frame', 'Object ID', 'Class', 'Traffic Status', 'Movement Direction', 'Entry/Exit Status'])
csv_df.to_csv('traffic_analysis_output.csv', index=False)

# Generate Business Insights Report
with open('business_insights.txt', 'w') as report:
    report.write('Traffic Analysis Report\n')
    report.write('----------------------------\n')
    report.write(f'Total Frames Processed: {frame_number}\n')
    report.write(f'Final Traffic Status: {traffic_status}\n')
    report.write(f'Heavy Traffic Threshold: {heavy_traffic_threshold} vehicles\n')
    report.write(f'Moderate Traffic Threshold: {moderate_traffic_threshold} vehicles\n')
    report.write('\nMovement Trends:\n')
    for obj_id, (last_x, last_y) in object_movement.items():
        report.write(f'Object {obj_id} final position: ({last_x}, {last_y})\n')
    
    # Recommendations
    report.write('\nRecommendations:\n')
    if traffic_status == 'Heavy Traffic':
        report.write('Suggest increasing green light duration in congested areas.\n')
    elif traffic_status == 'Moderate Traffic':
        report.write('Monitor traffic flow and consider signal adjustments if congestion increases.\n')
