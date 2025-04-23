import argparse


def parse_args_server():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-q", "--quiet", help="decrease output verbosity", action="store_true")
    parser.add_argument("-H", "--host", help="server IP address", required=True)
    parser.add_argument("-p", "--port", help="server port", type=int, required=True)
    parser.add_argument("-s", "--storage", help="storage dir path")
    parser.add_argument("-r", "--protocol", help="error recovery protocol", type=str)
    args = parser.parse_args()
    return args


def parse_args_client(command_type):
    if command_type == 'upload':
        program_name = 'upload'
        description = 'Client application to upload a file to the server'
    elif command_type == 'download':
        program_name = 'download'
        description = 'Client application to download a file from the server'
    else:
        raise ValueError("command_type must be either 'upload' or 'download'")

    parser = argparse.ArgumentParser(prog=program_name, description=description)

    verbosity_group = parser.add_mutually_exclusive_group()

    verbosity_group.add_argument('-v', '--verbose', action='store_true', help='increase output verbosity')
    verbosity_group.add_argument('-q', '--quiet', action='store_true', help='decrease output verbosity')
    parser.add_argument('-H', '--host', metavar='ADDR', help='server IP address')
    parser.add_argument('-p', '--port', type=int, help='server port')
    parser.add_argument('-n', '--name', metavar='FILENAME', help='file name')

    if command_type == 'upload':
        parser.add_argument('-s', '--src', metavar='FILEPATH', help='source file path')
    elif command_type == 'download':
        parser.add_argument('-d', '--dst', metavar='FILEPATH', help='destination file path')

    parser.add_argument('-r', '--protocol', help='error recovery protocol')

    args = parser.parse_args()
    return args
