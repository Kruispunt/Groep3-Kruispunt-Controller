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


def process_detection(detection, road_user):
    """
    Verwerk een individuele detectie voor een bepaald type weggebruiker (auto's, fietsers, voetgangers)
    en retourneer de toestand van de baan.
    """
    detected_states = []
    detect_cyclist_or_pedestrian = False  # Variabele om te controleren of een fietser of voetganger is gedetecteerd

    detected_states = []

    for detectie in detection:
        if road_user == "Cars":
            detect_near = detectie.get("DetectNear", False)
            detect_far = detectie.get("DetectFar", False)
            current_state = detectie.get("CurrentState", 0)  # Huidige staat van de baan

            if detect_near and not detect_far:
                if current_state == 0:
                    detected_states.append(2)
                elif current_state == 2:
                    detected_states.append(1)
            elif not detect_near and not detect_far:
                detected_states.append(0)
            elif detect_near and detect_far:
                detected_states.append(2)
            else:
                detected_states.append(current_state)
            pass

        elif road_user == "Cyclists":
            detect_cyclist = detectie.get("DetectCyclist", False)
            if detect_cyclist:
                detect_cyclist_or_pedestrian = True  # Een fietser is gedetecteerd
            detected_states.append(1 if detect_cyclist else 0)
            pass

        elif road_user == "Pedestrians":
            detect_pedestrians = detectie.get("DetectPedestrians", False)
            if detect_pedestrians:
                detect_cyclist_or_pedestrian = True  # Een voetganger is gedetecteerd
            detected_states.append(1 if detect_pedestrians else 0)
            pass
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
received_data = {}
def process_intersection():
    """
    Verwerk detecties op een kruispunt.
    """
    while True:
        for intersection, intersection_data in received_data.items():
            print(f"Checking intersection {intersection}:")

            for light, light_data in intersection_data.items():
                detected_pedestrian_or_cyclists = False
                json_data = generate_empty_json(intersection)
                print('reset')

                for road_user, detections in light_data.items():
                    detected_states = process_detection(detections, road_user)
                    print(f"  {road_user}: Detected at {light}: {detected_states}")
                    json_data[intersection][light][road_user] = detected_states

                    # Check for pedestrian or cyclist detection
                    if road_user in ["Cyclists", "Pedestrians"] and any(detected_states):
                        detected_pedestrian_or_cyclists = True

                # Reset car state if pedestrians or cyclists detected
                if detected_pedestrian_or_cyclists:
                    json_data[intersection][light]["Cars"] = [0, 0, 0, 0]


                # Simulate green light duration
                if 2 in json_data[intersection][light]['Cars']:
                    send_signal_to_simulation(json_data)
                    time.sleep(groen)
                    json_data[intersection][light]['Cars'] = [1, 1, 1, 1]
                    send_signal_to_simulation(json_data)
                    time.sleep(oranje)

                # Send JSON data to simulation
                send_signal_to_simulation(json_data)



def send_signal_to_simulation(json_data):
    """
    Stuur de JSON-data naar de simulatie.
    """
    print(json.dumps(json_data))
    c.send(json.dumps(json_data).encode())
    time.sleep(0.1)


def handle_client(c):
    global received_data
    """
    Behandel communicatie met de simulatie.
    """
    while True:
        # Wacht op informatie van de simulatie
        message = c.recv(2500)
        print('Received:', message)

        # Ontleed de ontvangen JSON-data
        received_data = json.loads(message)

        # voor development
        # received_data = {
        #             "1": {
        #                 "A": {
        #                     "Cars":
        #                         [
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False}
        #                         ],
        #                     "Cyclists":
        #                         [
        #                             {"DetectCyclist": False},
        #                             {"DetectCyclist": False}
        #                         ],
        #                     "Pedestrians":
        #                         [
        #                             {"DetectPedestrians": False},
        #                             {"DetectPedestrians": False},
        #                             {"DetectPedestrians": False},
        #                             {"DetectPedestrians": False}
        #                         ]
        #                 },
        #                 "B": {
        #                     "Cars":
        #                         [
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False}
        #                         ],
        #                     "Cyclists":
        #                         [
        #                             {"DetectCyclist": False},
        #                             {"DetectCyclist": False}
        #                         ],
        #                     "Pedestrians":
        #                         [
        #                             {"DetectPedestrians": False},
        #                             {"DetectPedestrians": False},
        #                             {"DetectPedestrians": False},
        #                             {"DetectPedestrians": False}
        #                         ],
        #                     "Busses":
        #                         [45, 67, 21]
        #                 },
        #                 "C": {
        #                     "Cars":
        #                         [
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False}
        #                         ]
        #                 }
        #             },
        #             "2": {
        #                 "D": {
        #                     "Cars":
        #                         [
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False}
        #                         ]
        #                     },
        #                 "E": {
        #                     "Cars":
        #                         [
        #                             {"DetectNear": True, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": True, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False}
        #                         ],
        #                     "Cyclists":
        #                         [
        #                             {"DetectCyclist": False},
        #                             {"DetectCyclist": False}
        #                         ],
        #                     "Pedestrians":
        #                         [
        #                             {"DetectPedestrians": False},
        #                             {"DetectPedestrians": False},
        #                             {"DetectPedestrians": False},
        #                             {"DetectPedestrians": False}
        #                         ],
        #                     "Busses":
        #                         [45, 67, 21]
        #                 },
        #                 "F": {
        #                     "Cars":
        #                         [
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False}
        #                         ],
        #                     "Cyclists":
        #                         [
        #                             {"DetectCyclist": False},
        #                             {"DetectCyclist": False}
        #                         ],
        #                     "Pedestrians":
        #                         [
        #                             {"DetectPedestrians": False},
        #                             {"DetectPedestrians": False},
        #                             {"DetectPedestrians": False},
        #                             {"DetectPedestrians": False}
        #                         ]
        #                 }
        #             }
        #         }
        # Check of er verkeer is op basis van ontvangen data



s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(5)

# Voor development
# handle_client(s)
while True:
    c, addr = s.accept()
    print('Got connection from', addr)
    threading.Thread(target=handle_client, args=(c,)).start()
    threading.Thread(target=process_intersection, args=()).start()
s.close()

