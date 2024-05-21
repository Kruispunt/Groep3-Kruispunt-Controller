from server import Server
from constants import HOST, PORT

if __name__ == "__main__":
    server = Server(HOST, PORT)
    server.run()
