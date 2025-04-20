import argparse

def parse_args_server():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity",action="store_true")
    parser.add_argument("-q", "--quiet", help="decrease output verbosity", action="store_true")
    parser.add_argument("-H", "--host", help="server IP address", required = True)
    parser.add_argument("-p", "--port", help="server port", type=int, required = True)
    parser.add_argument("-s", "--storage", help="storage dir path")
    parser.add_argument("-r", "--protocol", help="error recovery protocol", type=str)
    args = parser.parse_args()
    return args