from lib.args_parser import parse_args_client
import lib.client as client

def main():
    args = parse_args_client("upload")
    client.run_client(args, "upload")

if __name__ == "__main__":
    main()
