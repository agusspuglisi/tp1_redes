from lib.args_parser import parse_args_client
import lib.client as client

def main():
    args = parse_args_client("download")
    client.run_client(args, "download")

if __name__ == "__main__":
    main()
