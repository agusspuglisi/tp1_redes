import socket
from lib.args_parser import parse_args_client
 
def run_client(args, command):
    host, port = args.host, args.port
    message = args.name
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as c_socket:
        c_socket.sendto(message.encode(), (host, port))
        print(f"Sent message to {host}:{port}: {message}")
        response, _ = c_socket.recvfrom(2048)
        print(f"Received response: {response.decode()}")
 
if __name__ == "__main__":
    args = parse_args_client("upload")
    run_client(args)
 