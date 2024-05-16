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
    detected_states = [0] * len(detection)

    if road_user == "Cars":
        for index, detectie in enumerate(detection):
            if detectie.get("PrioCar", False):
                detected_states[index] = 2
                return detected_states
            if detectie.get("DetectNear", False) or detectie.get("DetectFar", False):
                detected_states[index] = 2  # Als detectie in de buurt is, zet de baanstatus op 2
    elif road_user == "Cyclists":
        detected_states = [2 if d.get("DetectCyclist", False) else 0 for d in detection]
    elif road_user == "Pedestrians":
        detected_states = [2 if d.get("DetectPedestrians", False) else 0 for d in detection]
    elif road_user == "Busses":
        if len(detection) > 0:
            detected_states = [[0,2] if detection[0] in [22,28,95,825,695] else 0]
    return detected_states


def generate_empty_json():
    """
    Genereer een JSON-sjabloon met alle punten en waarden ingesteld op 0 voor het opgegeven kruispunt.
    """
    return {
        '1': {
            'A': {"Cars": [0] * 4, "Cyclists": [0, 0], "Pedestrians": [0] * 4},
            'B': {"Cars": [0] * 4, "Cyclists": [0, 0], "Pedestrians": [0] * 4, "Busses": [0]},
            'C': {"Cars": [0] * 4}},
        '2':{
            'D': {"Cars": [0] * 4},
            'E': {"Cars": [0] * 3, "Cyclists": [0, 0], "Pedestrians": [0] * 4, "Busses": [0]},
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

        json_data = generate_empty_json()

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

def check_prio_car():
    """
    Controleer continu op de aanwezigheid van een PrioCar.
    Als een PrioCar wordt gedetecteerd, zet alle andere stoplichten op rood
    en het stoplicht van de PrioCar op groen.
    """
    while True:
        global received_data
        for intersection, intersection_data in received_data.items():
            for light, light_data in intersection_data.items():
                for road_user_data in light_data.values():
                    for detection in road_user_data:
                        if "PrioCar" in detection and detection["PrioCar"]:
                            # Zet alle stoplichten op rood
                            red_data = generate_empty_json()
                            print('Sending red:', json.dumps(red_data))
                            c.send(json.dumps(red_data).encode())

                            # Zet het stoplicht van de PrioCar op groen
                            prio_car_data = generate_empty_json()
                            prio_car_data[intersection][light]["Cars"] = [2] * len(light_data["Cars"])
                            print('Sending green for PrioCar:', json.dumps(prio_car_data))
                            c.send(json.dumps(prio_car_data).encode())
                            time.sleep(groen)
                            # Wacht een korte tijd voordat de volgende controle wordt uitgevoerd
                            time.sleep(1)
                            break  # Stop met zoeken zodra een PrioCar is gevonden
        # Wacht een korte tijd voordat de volgende controle wordt uitgevoerd
        time.sleep(1)
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

def send_and_wait(data):
    print('Sending data:', json.dumps(data))
    c.send(json.dumps(data).encode())
    time.sleep(groen)
    print('Sending orange:', json.dumps(set_oranje(data)))
    c.send(json.dumps(set_oranje(data)).encode())
    time.sleep(oranje)
    red_data = generate_empty_json()
    print('Sending red:', json.dumps(red_data))
    c.send(json.dumps(red_data).encode())
    time.sleep(5)

def send_cyclists_and_pedestrians(data):
    print('Sending green (cp):', json.dumps(data))
    c.send(json.dumps(data).encode())
    time.sleep(groen_fietsers)
    print('Sending orange(cp):', json.dumps(set_oranje(data)))
    c.send(json.dumps(set_oranje(data)).encode())
    time.sleep(oranje_fietsers)
    red_data = generate_empty_json()
    print('Sending red(cp):', json.dumps(red_data))
    c.send(json.dumps(red_data).encode())
    time.sleep(6)
def get_pedestrian_and_cyclists(json_data):
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
def cyclists_and_pedestrians(data):
    # Maak een kopie van de data om de originele niet te wijzigen
    modified_data = data.copy()

    # Loop door elk kruispunt en elke licht en pas de data aan
    for intersection, lights_data in modified_data.items():
        for light, light_data in lights_data.items():
            # Zet de data van Cars op 0
            modified_data[intersection][light]['Cars'] = [0] * len(light_data['Cars'])
            modified_data[intersection][light]['Busses'] = [0] * len(light_data['Cars'])
            # Zet alle data van Cyclists en Pedestrians op 2
            if 'Cyclists' in light_data:
                modified_data[intersection][light]['Cyclists'] = [2] * len(light_data['Cyclists'])
            if 'Pedestrians' in light_data:
                modified_data[intersection][light]['Pedestrians'] = [2] * len(light_data['Pedestrians'])
    return modified_data
def merge_and_send_to_simulation(json_data):
    """
    Combineer de JSON-gegevens van kruispunt 1 en kruispunt 2 en stuur deze naar de simulatie.
    """
    global received_data
    with simulation_lock:

        pedestrian_lists, cyclist_lists = get_pedestrian_and_cyclists(json_data)
        combined_data_AD = generate_empty_json()
        combined_data_BE = generate_empty_json()
        combined_data_CF = generate_empty_json()

        combined_data_AD["1"]["A"]["Cars"] = json_data["1"]["A"]["Cars"]
        combined_data_AD["2"]["D"]["Cars"] = json_data["2"]["D"]["Cars"]
        combined_data_AD["1"]["C"]["Cars"] = [0, 0] + json_data["1"]["C"]["Cars"][-2:]  # Voeg de eerste twee elementen van json_data["1"]["C"] toe
        combined_data_AD["2"]["E"]["Cars"] = [0] + json_data["2"]["E"]["Cars"][-2:]  # Voeg de eerste twee elementen van json_data["2"]["E"] toe

        if 2 in combined_data_AD["1"]["A"]["Cars"] or 2 in combined_data_AD["2"]["D"]["Cars"]:
            send_and_wait(combined_data_AD)

        combined_data_BE["1"]["B"]["Cars"] = json_data["1"]["B"]["Cars"]
        combined_data_BE["2"]["E"]["Cars"] = json_data["2"]["E"]["Cars"]
        combined_data_BE["1"]["A"]["Cars"] = [0, 0] + json_data["1"]["A"]["Cars"][-2:]  # Voeg de eerste twee elementen van json_data["1"]["A"] toe
        combined_data_BE["2"]["F"]["Cars"] = [0, 0] + json_data["2"]["F"]["Cars"][-2:]  # Voeg de eerste twee elementen van json_data["2"]["F"] toe

        if 2 in combined_data_BE["1"]["B"]["Cars"] or 2 in combined_data_BE["2"]["E"]["Cars"]:
            send_and_wait(combined_data_BE)

        combined_data_CF["1"]["C"]["Cars"] = json_data["1"]["C"]["Cars"]
        combined_data_CF["2"]["F"]["Cars"] = json_data["2"]["F"]["Cars"]
        combined_data_CF["2"]["D"]["Cars"] = [0,0] + json_data["2"]["D"]["Cars"][-2:]  # Voeg de eerste twee elementen van json_data["2"]["E"] toe
        combined_data_CF["1"]["B"]["Busses"] = [2] if any(bus in [22, 28, 95, 825, 695] for bus in received_data.get("1", {}).get("B", {}).get("Busses", [])) else [0]

        if 2 in combined_data_CF["1"]["C"]["Cars"] or 2 in combined_data_CF["2"]["F"]["Cars"]:
            send_and_wait(combined_data_CF)

        if any(2 in sublist for sublist in pedestrian_lists) or any(2 in sublist for sublist in cyclist_lists):
            send_cyclists_and_pedestrians(cyclists_and_pedestrians(json_data))

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
        #                             {"DetectNear": True, "DetectFar": False, "PrioCar": False}
        #                         ],
        #                     "Cyclists":
        #                         [
        #                             {"DetectCyclist": True},
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
        #                         [95,28]
        #                 },
        #                 "C": {
        #                     "Cars":
        #                         [
        #                             {"DetectNear": True, "DetectFar": False, "PrioCar": False},
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
        #                             {"DetectNear": False, "DetectFar": True, "PrioCar": False},
        #                             {"DetectNear": True, "DetectFar": True, "PrioCar": False},
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
# threading.Thread(target=check_prio_car).start()
while True:
    c, addr = s.accept()
    print('Got connection from', addr)
    # Voor elke verbinding start een nieuwe thread om de client te behandelen
    threading.Thread(target=handle_client, args=(c,)).start()
    threading.Thread(target=process_intersection, args=()).start()
    threading.Thread(target=check_prio_car).start()

s.close()
