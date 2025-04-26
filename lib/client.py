import socket

def run_client(args, command_type):
    host, port = args.host, args.port
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s_socket:
        s_socket.bind((host, port))
    print("Client started on {}:{}".format(host, port))
