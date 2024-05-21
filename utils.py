def generate_empty_json():
    return {
        '1': {'A': {"Cars": [0] * 4, "Cyclists": [0, 0], "Pedestrians": [0] * 4},
              'B': {"Cars": [0] * 4, "Cyclists": [0, 0], "Pedestrians": [0] * 4, "Busses": [0]},
              'C': {"Cars": [0] * 4}},
        '2': {'D': {"Cars": [0] * 4},
              'E': {"Cars": [0] * 3, "Cyclists": [0, 0], "Pedestrians": [0] * 4, "Busses": [0]},
              'F': {"Cars": [0] * 4, "Cyclists": [0, 0], "Pedestrians": [0] * 4}}
    }

def set_oranje(data):
    for intersection, lights_data in data.items():
        for light, light_data in lights_data.items():
            for road_user, detections in light_data.items():
                if isinstance(detections, list):
                    data[intersection][light][road_user] = [1 if d == 2 else d for d in detections]
                else:
                    data[intersection][light][road_user] = 1 if detections == 2 else detections
    return data
