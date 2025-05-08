from lib.args_parser import parse_args_client
from lib.client import run_client


def main():
    args = parse_args_client("upload")
    run_client(args, "upload")


if __name__ == "__main__":
    main()
