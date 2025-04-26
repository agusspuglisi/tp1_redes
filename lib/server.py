import socket

def run_server(args):
    host, port = args.host, args.port #args.storage, args.protocol
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s_socket:
        s_socket.bind((host, port))
        print("Server started on {}:{}".format(host, port))
    