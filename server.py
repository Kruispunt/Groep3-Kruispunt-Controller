import socket
import threading
from traffic_light_controller import TrafficLightController
class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.controller = TrafficLightController()

    def handle_client(self, client_socket):
        while True:
            message = client_socket.recv(5000)
            if not message:
                break
            self.controller.update_received_data(message)

    def run(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)

        while True:
            client_socket, addr = server_socket.accept()
            print('Got connection from', addr)
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            threading.Thread(target=self.controller.process_intersection, args=(client_socket,)).start()
