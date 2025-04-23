from lib.args_parser import parse_args_server
import lib.server as server

def main():
    args = parse_args_server()  # noqa: F841
    server.run_server(args)


if __name__ == "__main__":
    main()
