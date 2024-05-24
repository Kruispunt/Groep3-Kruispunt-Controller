import json
import time
import threading
from utils import generate_empty_json, set_oranje
from constants import DURATION_EVACUATION_CARS, DURATION_ORANGE, DURATION_GREEN, DURATION_GREEN_CYCLISTS, DURATION_ORANGE_CYCLISTS, DURATION_EVACUATION_CYCLISTS


class TrafficLightController:
    def __init__(self):
        self.received_data = {}
        self.simulation_lock = threading.Lock()

    def update_received_data(self, message):
        with self.simulation_lock:
            self.received_data = json.loads(message)

    def process_detection(self, detection, road_user):
        detected_states = [0] * len(detection)
        if road_user == "Cars":
            for index, detectie in enumerate(detection):
                if detectie.get("DetectNear", False) or detectie.get("DetectFar", False):
                    detected_states[index] = 2
        elif road_user == "Cyclists":
            detected_states = [2 if d.get("DetectCyclist", False) else 0 for d in detection]
        elif road_user == "Pedestrians":
            detected_states = [2 if d.get("DetectPedestrians", False) else 0 for d in detection]
        return detected_states

    def process_intersection(self, client_socket):
        while True:
            json_data = generate_empty_json()

            with self.simulation_lock:
                for intersection_id, intersection_data in self.received_data.items():
                    for light, light_data in intersection_data.items():
                        for road_user, detections in light_data.items():
                            json_data[intersection_id][light][road_user] = self.process_detection(detections, road_user)

            self.merge_and_send_to_simulation(client_socket, json_data)
            time.sleep(1)

    def merge_and_send_to_simulation(self, client_socket, json_data):
        pedestrian_lists, cyclist_lists = self.get_pedestrian_and_cyclists(json_data)
        combined_data_AD = generate_empty_json()
        combined_data_BE = generate_empty_json()
        combined_data_CF = generate_empty_json()

        combined_data_AD["1"]["A"]["Cars"] = [2,2,2,2]
        combined_data_AD["2"]["D"]["Cars"] = [2,2,2,2]
        combined_data_AD["1"]["C"]["Cars"] = [0, 0, 2, 2] if 2 in json_data["1"]["C"]["Cars"][-2:] else [0, 0, 0, 0]
        combined_data_AD["2"]["E"]["Cars"] = [0] + json_data["2"]["E"]["Cars"][-2:]
        print('bussen:',self.received_data.get("2", {}).get("E", {}).get("Busses", []))
        combined_data_AD['2']["E"]["Busses"] = [0,2] if any(
            bus in [22, 28, 95, 825, 695] for bus in self.received_data.get("2", {}).get("E", {}).get("Busses", [])) else [0]

        if 2 in combined_data_AD["1"]["A"]["Cars"] or 2 in combined_data_AD["2"]["D"]["Cars"]:
            print("(A)Based on", self.received_data)
            print("(A)Sending AD", combined_data_AD)
            self.send_and_wait(client_socket, combined_data_AD, DURATION_GREEN, DURATION_ORANGE)

        combined_data_BE["1"]["B"]["Cars"] = [2,2,2,2]
        combined_data_BE["2"]["E"]["Cars"] = [2,2,2,2]
        combined_data_BE["1"]["A"]["Cars"] = [0, 0] + json_data["1"]["A"]["Cars"][-2:]
        combined_data_BE["2"]["F"]["Cars"] = [0, 0, 2, 2] if 2 in json_data["2"]["F"]["Cars"][-2:] else [0, 0, 0, 0]
        combined_data_BE['2']["E"]["Busses"] = [2,0] if any(
            bus in [14, 114, 320] for bus in self.received_data.get("2", {}).get("E", {}).get("Busses", [])) else [0]

        if 2 in combined_data_BE["1"]["B"]["Cars"] or 2 in combined_data_BE["2"]["E"]["Cars"]:
            print("(B)Based on", self.received_data)
            print("(B)Sending BE", combined_data_BE)
            self.send_and_wait(client_socket, combined_data_BE, DURATION_GREEN, DURATION_ORANGE)

        combined_data_CF["1"]["C"]["Cars"] = [2,2,2,2]
        combined_data_CF["2"]["F"]["Cars"] = [2,2,2,2]
        combined_data_CF["2"]["D"]["Cars"] = [0, 0, 2, 2] if 2 in json_data["2"]["D"]["Cars"][-2:] else [0, 0, 0, 0]
        combined_data_CF["1"]["B"]["Busses"] = [2] if any(
            bus in [22, 28, 95, 825, 695] for bus in self.received_data.get("1", {}).get("B", {}).get("Busses", [])) else [0]
        if 2 in combined_data_CF["1"]["C"]["Cars"] or 2 in combined_data_CF["2"]["F"]["Cars"]:
            print("(C)Based on", self.received_data)
            print("(C)Sending CF", combined_data_CF)
            self.send_and_wait(client_socket, combined_data_CF, DURATION_GREEN, DURATION_ORANGE)

        if any(2 in sublist for sublist in pedestrian_lists) or any(2 in sublist for sublist in cyclist_lists):
            self.send_cyclists_and_pedestrians(client_socket, self.cyclists_and_pedestrians(json_data))

    def send_and_wait(self, client_socket, data, green_duration, orange_duration):
        client_socket.send(json.dumps(data).encode())
        time.sleep(green_duration)
        client_socket.send(json.dumps(set_oranje(data)).encode())
        time.sleep(orange_duration)
        client_socket.send(json.dumps(generate_empty_json()).encode())
        time.sleep(DURATION_EVACUATION_CARS)

    def send_cyclists_and_pedestrians(self, client_socket, data):
        self.send_and_wait(client_socket, data, DURATION_GREEN_CYCLISTS, DURATION_ORANGE_CYCLISTS)

    def get_pedestrian_and_cyclists(self, json_data):
        pedestrian_lists = [
            json_data["1"]["A"]["Pedestrians"],
            json_data["1"]["B"]["Pedestrians"],
            json_data["2"]["E"]["Pedestrians"],
            json_data["2"]["F"]["Pedestrians"]
        ]

        cyclist_lists = [
            json_data["1"]["A"]["Cyclists"],
            json_data["1"]["B"]["Cyclists"],
            json_data["2"]["E"]["Cyclists"],
            json_data["2"]["F"]["Cyclists"]
        ]
        return pedestrian_lists, cyclist_lists

    def cyclists_and_pedestrians(self, data):
        modified_data = data.copy()
        for intersection, lights_data in modified_data.items():
            for light, light_data in lights_data.items():
                modified_data[intersection][light]['Cars'] = [0] * len(light_data['Cars'])
                if 'Busses' in light_data:
                    modified_data[intersection][light]['Busses'] = [0] * len(light_data['Busses'])
                if 'Cyclists' in light_data:
                    modified_data[intersection][light]['Cyclists'] = [2] * len(light_data['Cyclists'])
                if 'Pedestrians' in light_data:
                    modified_data[intersection][light]['Pedestrians'] = [2] * len(light_data['Pedestrians'])
        return modified_data