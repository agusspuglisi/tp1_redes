from lib.args_parser import parse_args_client
from lib.client import download_file

def main():
    args = parse_args_client("download")
    download_file(args)

if __name__ == "__main__":
    main()
