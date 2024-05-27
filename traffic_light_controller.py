import json
import time
import threading
from utils import generate_empty_json, set_oranje
from constants import (
    DURATION_EVACUATION_CARS, DURATION_ORANGE, DURATION_GREEN,
    DURATION_GREEN_CYCLISTS, DURATION_ORANGE_CYCLISTS
)


class TrafficLightController:
    def __init__(self):
        self.received_data = {}
        self.simulation_lock = threading.Lock()
        self.prio_car_detected = False

    def update_received_data(self, message):
        """Updates the received data with the provided JSON message."""
        with self.simulation_lock:
            self.received_data = json.loads(message)

    def process_detection(self, detection, road_user):
        """Processes detection data and returns the detected states based on the road user type."""
        detected_states = [0] * len(detection)
        if road_user == "Cars":
            for index, detectie in enumerate(detection):
                if detectie.get("PrioCar", False):
                    detected_states[index] = 2
                    self.prio_car_detected = True
                if detectie.get("DetectNear", False) or detectie.get("DetectFar", False):
                    detected_states[index] = 2
        elif road_user == "Cyclists":
            detected_states = [2 if d.get("DetectCyclist", False) else 0 for d in detection]
        elif road_user == "Pedestrians":
            detected_states = [2 if d.get("DetectPedestrians", False) else 0 for d in detection]
        return detected_states

    def process_intersection(self, client_socket):
        """Continuously processes intersection data and sends appropriate signals to the client."""
        while True:
            json_data = generate_empty_json()

            with self.simulation_lock:
                for intersection_id, intersection_data in self.received_data.items():
                    for light, light_data in intersection_data.items():
                        for road_user, detections in light_data.items():
                            json_data[intersection_id][light][road_user] = self.process_detection(detections, road_user)

            if self.prio_car_detected:
                self.handle_priocars(client_socket)
            else:
                self.send_AD(client_socket, json_data)
                self.send_BE(client_socket, json_data)
                self.send_CF(client_socket, json_data)
                self.send_CP(client_socket, json_data)

            self.prio_car_detected = False
            time.sleep(1)

    def handle_priocars(self, client_socket):
        """Handles priority cars by sending green signals to the corresponding lanes."""
        for intersection_id, intersection_data in self.received_data.items():
            for light, light_data in intersection_data.items():
                priocar_detections = light_data.get('Priocars', [])
                for priocar_detect in priocar_detections:
                    if priocar_detect.get("DetectPriocar", False):
                        self.send_priocar_green_signal(client_socket, intersection_id, light)
                        break

    def send_priocar_green_signal(self, client_socket, intersection_id, light):
        """Sends a green signal for priority cars and waits for the specified durations."""
        priocar_green_data = generate_empty_json()
        priocar_green_data[intersection_id][light]['Cars'] = [2] * len(priocar_green_data[intersection_id][light]['Cars'])
        self.send_and_wait(client_socket, priocar_green_data, DURATION_GREEN, DURATION_ORANGE)

    def send_AD(self, client_socket, json_data):
        """Sends the AD signal configuration to the client."""
        combined_data = generate_empty_json()

        # Specific signal configurations
        combined_data['2']["E"]["Busses"] = [0, 2] if any(
            bus in [22, 28, 95, 825, 695] for bus in self.received_data.get("2", {}).get("E", {}).get("Busses", [])
        ) else [0, 0]

        self.send_and_wait_bus(client_socket, combined_data, len(self.received_data.get("2", {}).get("E", {}).get("Busses", [])))

        combined_data["1"]["A"]["Cars"] = [2, 2, 2, 2]
        combined_data["2"]["D"]["Cars"] = [2, 2, 2, 2]
        combined_data["1"]["C"]["Cars"] = [0, 0, 2, 2] if 2 in json_data["1"]["C"]["Cars"][-2:] else [0, 0, 0, 0]
        combined_data["2"]["E"]["Cars"] = [0] + json_data["2"]["E"]["Cars"][-2:]

        print("(A) Based on", self.received_data)
        print("(A) Sending AD", combined_data)
        self.send_and_wait(client_socket, combined_data, DURATION_GREEN, DURATION_ORANGE)

    def send_BE(self, client_socket, json_data):
        """Sends the BE signal configuration to the client."""
        combined_data = generate_empty_json()

        # Specific signal configurations
        combined_data["1"]["B"]["Cars"] = [2, 2, 2, 2]
        combined_data["2"]["E"]["Cars"] = [2, 2, 2, 2]
        combined_data["1"]["A"]["Cars"] = [0, 0] + json_data["1"]["A"]["Cars"][-2:]
        combined_data["2"]["F"]["Cars"] = [0, 0, 2, 2]
        combined_data['2']["E"]["Busses"] = [2, 0] if any(
            bus in [14, 114, 320] for bus in self.received_data.get("2", {}).get("E", {}).get("Busses", [])
        ) else [0, 0]

        print("(B) Based on", self.received_data)
        print("(B) Sending BE", combined_data)
        self.send_and_wait(client_socket, combined_data, DURATION_GREEN, DURATION_ORANGE)

    def send_CF(self, client_socket, json_data):
        """Sends the CF signal configuration to the client."""
        combined_data = generate_empty_json()

        # Specific signal configurations
        combined_data["1"]["C"]["Cars"] = [2, 2, 2, 2]
        combined_data["2"]["F"]["Cars"] = [2, 2, 2, 2]
        combined_data["2"]["D"]["Cars"] = [0, 0, 2, 2]
        combined_data["1"]["B"]["Busses"] = [2] if any(
            bus in [22, 28, 95, 825, 695] for bus in self.received_data.get("1", {}).get("B", {}).get("Busses", [])
        ) else [0]

        print("(C) Based on", self.received_data)
        print("(C) Sending CF", combined_data)
        self.send_and_wait(client_socket, combined_data, DURATION_GREEN, DURATION_ORANGE)

    def send_CP(self, client_socket, json_data):
        """Sends the CP signal configuration for cyclists and pedestrians to the client if required."""
        pedestrian_lists, cyclist_lists = self.get_pedestrian_and_cyclists(json_data)
        if any(2 in sublist for sublist in pedestrian_lists) or any(2 in sublist for sublist in cyclist_lists):
            self.send_cyclists_and_pedestrians(client_socket, self.cyclists_and_pedestrians(json_data))

    def send_and_wait(self, client_socket, data, green_duration, orange_duration):
        """Sends the signal data to the client and waits for the specified durations."""
        print("Sending:", data)
        client_socket.send(json.dumps(data).encode())
        time.sleep(green_duration)
        client_socket.send(json.dumps(set_oranje(data)).encode())
        time.sleep(orange_duration)
        client_socket.send(json.dumps(generate_empty_json()).encode())
        time.sleep(DURATION_EVACUATION_CARS)

    def send_and_wait_bus(self, client_socket, data, green_duration):
        """Sends the bus signal data to the client and waits for the specified duration."""
        print("Sending:", data)
        client_socket.send(json.dumps(data).encode())
        time.sleep(green_duration)

    def send_cyclists_and_pedestrians(self, client_socket, data):
        """Sends the signal data for cyclists and pedestrians and waits for the specified durations."""
        self.send_and_wait(client_socket, data, DURATION_GREEN_CYCLISTS, DURATION_ORANGE_CYCLISTS)

    def get_pedestrian_and_cyclists(self, json_data):
        """Returns lists of pedestrian and cyclist detection states."""
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
        """Modifies the signal data to prioritize cyclists and pedestrians."""
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
