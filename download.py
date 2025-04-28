from lib.args_parser import parse_args_client
from lib.client import run_client


def main():
    args = parse_args_client("download")
    run_client(args, "download")


if __name__ == "__main__":
    main()
