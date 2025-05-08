from lib.args_parser import parse_args_server
from lib.server import run_server


def main():
    args = parse_args_server()
    try:
        run_server(args)
    except KeyboardInterrupt:
        print("\nServer stopped by user.")


if __name__ == "__main__":
    main()
