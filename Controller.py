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
    detected_states = [0, 0, 0, 0]

    if road_user == "Cars":
        for index, detectie in enumerate(detection):
            if detectie.get("DetectNear", False) or detectie.get("DetectFar", False):
                detected_states[index] = 2  # Als detectie in de buurt is, zet de baanstatus op 2
    elif road_user == "Cyclists":
        detected_states = [2 if d.get("DetectCyclist", False) else 0 for d in detection]
    elif road_user == "Pedestrians":
        detected_states = [2 if d.get("DetectPedestrians", False) else 0 for d in detection]
    elif road_user == "Busses":
        detected_states = [2 if detection[0] in [22,28,95,825,695] else 0]
    elif road_user == "PrioCar":
        detected_states = [2 if detection else 0]  # Als PrioCar wordt gedetecteerd, zet het licht meteen op groen

    return detected_states


def generate_empty_json(intersection):
    """
    Genereer een JSON-sjabloon met alle punten en waarden ingesteld op 0 voor het opgegeven kruispunt.
    """
    return {
        '1': {
            'A': {"Cars": [0] * 4, "Cyclists": [0, 0], "Pedestrians": [0] * 4},
            'B': {"Cars": [0] * 4, "Cyclists": [0, 0], "Pedestrians": [0] * 4, "Busses": []},
            'C': {"Cars": [0] * 4}},
        '2':{
            'D': {"Cars": [0] * 4},
            'E': {"Cars": [0] * 3, "Cyclists": [0, 0], "Pedestrians": [0] * 4, "Busses": []},
            'F': {"Cars": [0] * 4, "Cyclists": [0, 0], "Pedestrians": [0] * 4}
        }
    }


def process_intersection():
    """
    Verwerk detecties op beide kruispunten.
    """
    while True:
        global received_data
        intersection_1_data = received_data.get('1', {})
        intersection_2_data = received_data.get('2', {})

        json_data = generate_empty_json('1')

        for light, light_data in intersection_1_data.items():
            current_light = light
            for road_user, detections in light_data.items():
                detected_states = process_detection(detections, road_user)
                json_data['1'][current_light][road_user] = detected_states

        for light, light_data in intersection_2_data.items():
            current_light = light
            for road_user, detections in light_data.items():
                detected_states = process_detection(detections, road_user)
                json_data['2'][current_light][road_user] = detected_states

        merge_and_send_to_simulation(json_data)

def set_oranje(combined_data):
    oranje_lichten = combined_data
    for intersection, lights_data in combined_data.items():
        for light, light_data in lights_data.items():
            for road_user, detections in light_data.items():
                if isinstance(detections, list):
                    oranje_lichten[intersection][light][road_user] = [1 if d == 2 else d for d in detections]
                else:
                    oranje_lichten[intersection][light][road_user] = 1 if detections == 2 else detections
    return oranje_lichten



def merge_and_send_to_simulation(json_data):
    """
    Combineer de JSON-gegevens van kruispunt 1 en kruispunt 2 en stuur deze naar de simulatie.
    """
    global received_data
    with simulation_lock:
        combined_data_AD = generate_empty_json('1')
        combined_data_BE = generate_empty_json('1')
        combined_data_CF = generate_empty_json('1')

        combined_data_AD["1"]["A"] = json_data["1"]["A"]
        combined_data_AD["2"]["D"] = json_data["2"]["D"]
        # combined_data_AD["1"]["C"] = json_data["1"]["C"][:2] + [0,0]  # Voeg de eerste twee elementen van json_data["1"]["C"] toe

        combined_data_BE["1"]["B"] = json_data["1"]["B"]
        combined_data_BE["2"]["E"] = json_data["2"]["E"]

        combined_data_CF["1"]["C"] = json_data["1"]["C"]
        combined_data_CF["2"]["F"] = json_data["2"]["F"]

        print('Send A+D:', json.dumps(combined_data_AD))
        c.send(json.dumps(combined_data_AD).encode())
        time.sleep(groen)
        print('Oranje A+D:', json.dumps(set_oranje(combined_data_AD)))
        c.send(json.dumps(set_oranje(combined_data_AD)).encode())  # Hier moet set_oranje gebruikt worden
        time.sleep(oranje)

        print('Send B+E:', json.dumps(combined_data_BE))
        c.send(json.dumps(combined_data_BE).encode())
        time.sleep(groen)
        print('Oranje B+E:', json.dumps(set_oranje(combined_data_BE)))
        c.send(json.dumps(set_oranje(combined_data_BE)).encode())  # Hier moet set_oranje gebruikt worden
        time.sleep(oranje)

        print('Send C+F', json.dumps(combined_data_CF))
        c.send(json.dumps(combined_data_CF).encode())
        time.sleep(groen)
        print('Oranje C+F:', json.dumps(set_oranje(combined_data_CF)))
        c.send(json.dumps(set_oranje(combined_data_CF)).encode())  # Hier moet set_oranje gebruikt worden
        time.sleep(oranje)

def handle_client(c):
    """
    Behandel communicatie met de simulatie.
    """
    global received_data
    global json_data
    while True:
        # Wacht op informatie van de simulatie
        message = c.recv(5000)
        print('Received:', message)

        # Ontleed de ontvangen JSON-data
        received_data = json.loads(message)

        # voor development
        # received_data = {
        #             "1": {
        #                 "A": {
        #                     "Cars":
        #                         [
        #                             {"DetectNear": True, "DetectFar": False, "PrioCar": False},
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
        #                         [14,22,1]
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
        #                             {"DetectNear": True, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False}
        #                         ]
        #                     },
        #                 "E": {
        #                     "Cars":
        #                         [
        #                             {"DetectNear": False, "DetectFar": False, "PrioCar": False},
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
        #                         [0]
        #                 },
        #                 "F": {
        #                     "Cars":
        #                         [
        #                             {"DetectNear": True, "DetectFar": False, "PrioCar": False},
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

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(5)

# Start threads voor het verwerken van elk kruispunt
# threading.Thread(target=handle_client, args=(s,)).start()
# threading.Thread(target=process_intersection, args=()).start()
while True:
    c, addr = s.accept()
    print('Got connection from', addr)
    # Voor elke verbinding start een nieuwe thread om de client te behandelen
    threading.Thread(target=handle_client, args=(c,)).start()
    threading.Thread(target=process_intersection, args=()).start()

s.close()
