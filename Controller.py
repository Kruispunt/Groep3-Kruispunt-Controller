import socket
import time
import json
import threading

# Definieer het doeladres en poort voor de C#-simulatie
HOST = 'localhost'  # Het IP-adres van de doelcomputer
PORT = 8080  # De poort waarop de C#-simulatie luistert

# Tijd in seconden voor groen licht
groen = 5
oranje = 2

groen_fietsers = 10
oranje_fietsers = 2

received_data = {}
simulation_lock = threading.Lock()  # Om gelijktijdige toegang tot de simulatie te voorkomen

def process_detection(detection, road_user):
    """
    Verwerk een individuele detectie voor een bepaald type weggebruiker (auto's, fietsers, voetgangers)
    en retourneer de toestand van de baan.
    """
    detected_states = [0, 0, 0, 0]  # Standaardstatus voor elke baan

    if road_user == "Cars":
        for index, detectie in enumerate(detection):
            if detectie.get("DetectNear", False) or detectie.get("DetectFar", False):
                detected_states[index] = 2  # Als detectie in de buurt is, zet de baanstatus op 2
    elif road_user == "Cyclists":
        detected_states = [2 if d.get("DetectCyclist", False) else 0 for d in detection]
    elif road_user == "Pedestrians":
        detected_states = [2 if d.get("DetectPedestrians", False) else 0 for d in detection]
    elif road_user == "PrioCar":
        detected_states = [2 if detection else 0]  # Als PrioCar wordt gedetecteerd, zet het licht meteen op groen

    return detected_states


def generate_empty_json(intersection):
    """
    Genereer een JSON-sjabloon met alle punten en waarden ingesteld op 0 voor het opgegeven kruispunt.
    """
    return {
        '1': {
            'A': {"Cars": [0, 0, 0, 0], "Cyclists": [0, 0], "Pedestrians": [0, 0, 0, 0]},
            'B': {"Cars": [0, 0, 0, 0], "Cyclists": [0, 0], "Pedestrians": [0, 0, 0, 0], "Busses": [1]},
            'C': {"Cars": [0, 0, 0, 0], "Cyclists": [0, 0], "Pedestrians": [0, 0, 0, 0]}},
        '2':{
            'D': {"Cars": [0, 0, 0, 0], "Cyclists": [0, 0], "Pedestrians": [0, 0, 0, 0]},
            'E': {"Cars": [0, 0, 0, 0], "Cyclists": [0, 0], "Pedestrians": [0, 0, 0, 0], "Busses": [1,0]},
            'F': {"Cars": [0, 0, 0, 0], "Cyclists": [0, 0], "Pedestrians": [0, 0, 0, 0]}
        }
    }

def process_intersection_1():
    """
    Verwerk detecties op kruispunt 1.
    """
    while True:
        global received_data
        intersection_data = received_data.get('1', {})
        for light, light_data in intersection_data.items():
            json_data = generate_empty_json('1')
            detected_pedestrian_or_cyclists = False
            for road_user, detections in light_data.items():
                detected_states = process_detection(detections, road_user)
                json_data['1'][light][road_user] = detected_states
                if "Pedestrians" in detected_states or "Cyclists" in detected_states:
                    detected_pedestrian_or_cyclists = True

            if not detected_pedestrian_or_cyclists:
                merge_and_send_to_simulation(json_data)
                time.sleep(groen)
                json_data['1'][light]['Cars'] = [1, 1, 1, 1]
                merge_and_send_to_simulation(json_data)
                time.sleep(oranje)


def process_intersection_2():
    """
    Verwerk detecties op kruispunt 1.
    """
    while True:
        global received_data
        intersection_data = received_data.get('2', {})
        for light, light_data in intersection_data.items():
            json_data = generate_empty_json('2')
            detected_pedestrian_or_cyclists = False
            for road_user, detections in light_data.items():
                detected_states = process_detection(detections, road_user)
                json_data['2'][light][road_user] = detected_states
                if "Pedestrians" in detected_states or "Cyclists" in detected_states:
                    detected_pedestrian_or_cyclists = True

            if not detected_pedestrian_or_cyclists:
                merge_and_send_to_simulation(json_data)
                time.sleep(groen)
                json_data['2'][light]['Cars'] = [1, 1, 1, 1]
                merge_and_send_to_simulation(json_data)
                time.sleep(oranje)
def merge_and_send_to_simulation(json_data):
    """
    Combineer de JSON-gegevens van kruispunt 1 en kruispunt 2 en stuur deze naar de simulatie.
    """
    global received_data
    with simulation_lock:
        combined_data = {"1": {}, "2": {}}
        combined_data["1"].update(json_data['1'])
        combined_data["2"].update(json_data['2'])
        # c.send(json.dumps(combined_data).encode())
        print('Merged and sent to simulation:', json.dumps(combined_data))
        time.sleep(0.1)

def handle_client(c):
    """
    Behandel communicatie met de simulatie.
    """
    global received_data
    global json_data
    while True:
        # Wacht op informatie van de simulatie
        # message = c.recv(2500)
        # print('Received:', message)

        # Ontleed de ontvangen JSON-data
        # received_data = json.loads(message)

        # voor development
        received_data = {
                    "1": {
                        "A": {
                            "Cars":
                                [
                                    {"DetectNear": True, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False}
                                ],
                            "Cyclists":
                                [
                                    {"DetectCyclist": False},
                                    {"DetectCyclist": False}
                                ],
                            "Pedestrians":
                                [
                                    {"DetectPedestrians": False},
                                    {"DetectPedestrians": False},
                                    {"DetectPedestrians": False},
                                    {"DetectPedestrians": False}
                                ]
                        },
                        "B": {
                            "Cars":
                                [
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False}
                                ],
                            "Cyclists":
                                [
                                    {"DetectCyclist": False},
                                    {"DetectCyclist": False}
                                ],
                            "Pedestrians":
                                [
                                    {"DetectPedestrians": False},
                                    {"DetectPedestrians": False},
                                    {"DetectPedestrians": False},
                                    {"DetectPedestrians": False}
                                ],
                            "Busses":
                                []
                        },
                        "C": {
                            "Cars":
                                [
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False}
                                ]
                        }
                    },
                    "2": {
                        "D": {
                            "Cars":
                                [
                                    {"DetectNear": True, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False}
                                ]
                            },
                        "E": {
                            "Cars":
                                [
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": True, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False}
                                ],
                            "Cyclists":
                                [
                                    {"DetectCyclist": False},
                                    {"DetectCyclist": False}
                                ],
                            "Pedestrians":
                                [
                                    {"DetectPedestrians": False},
                                    {"DetectPedestrians": False},
                                    {"DetectPedestrians": False},
                                    {"DetectPedestrians": False}
                                ],
                            "Busses":
                                [0]
                        },
                        "F": {
                            "Cars":
                                [
                                    {"DetectNear": True, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False},
                                    {"DetectNear": False, "DetectFar": False, "PrioCar": False}
                                ],
                            "Cyclists":
                                [
                                    {"DetectCyclist": False},
                                    {"DetectCyclist": False}
                                ],
                            "Pedestrians":
                                [
                                    {"DetectPedestrians": False},
                                    {"DetectPedestrians": False},
                                    {"DetectPedestrians": False},
                                    {"DetectPedestrians": False}
                                ]
                        }
                    }
                }

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(5)

# Start threads voor het verwerken van elk kruispunt
threading.Thread(target=handle_client, args=(s,)).start()
threading.Thread(target=process_intersection_1, args=()).start()
threading.Thread(target=process_intersection_2, args=()).start()
while True:
    c, addr = s.accept()
    print('Got connection from', addr)
    # Voor elke verbinding start een nieuwe thread om de client te behandelen
    threading.Thread(target=handle_client, args=(c,)).start()

s.close()
