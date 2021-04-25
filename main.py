#!.venv/bin/python3

from google.cloud import storage
from glob import glob
import humanize
from datetime import datetime, timedelta
import argparse
import random
import string
import yaml
import os

from oauth2client.service_account import ServiceAccountCredentials


def load_config():
    try:
        return yaml.safe_load(open(os.path.expanduser("~/.stfurc")))
    except FileNotFoundError:
        print("config file wasn't found, try running \"stfu --init\" to create it")
        exit(1)
    except yaml.YAMLError:
        print("Config file couldn't be read, please check syntax")
        exit(1)


def initialize():
    conf = {
        "project": input("Enter projectID: "),
        "bucket": input("Enter bucket name: "),
        "service-account-json-path": input("Enter path of service-account JSON file:")
    }
    yaml.dump(conf, open(os.path.expanduser("~/.stfurc"), "w"))

    c = storage.Client(project=conf['project'])
    if conf['bucket'] not in [i.name for i in c.list_buckets()]:
        c.create_bucket(conf['bucket'])


def format_list(files, size=False, date=False):
    if len(files) == 0:
        print("No files found")

    for k, v in files.items():
        print(k)
        for i, value in enumerate(v):
            name = value['name']
            created = value['created'].strftime("%d-%m-%Y %H:%M")
            human_size = humanize.naturalsize(value['size'])

            extra_info = ""
            if date:
                extra_info += f" | {created}"
            if size:
                extra_info += f" | {human_size}"

            if i == len(v) - 1:
                print(f" └ {name}{extra_info}")
            else:
                print(f" ├ {name}{extra_info}")


def download(client, files):
    b = client.get_bucket(load_config()['bucket'])
    for target in files:
        for k, v in list_files(client).items():
            for f in v:
                if f['name'] == target:
                    ext = f['name'].split('.')[-1]
                    blob = b.get_blob(f"{ext}/{f['name']}")
                    blob.download_to_filename(f"./{f['name'][7::]}")


def share_file(client, files):
    b = client.get_bucket(load_config()['bucket'])
    for target in files:
        for k, v in list_files(client).items():
            for f in v:
                if f['name'] == target:
                    ext = f['name'].split('.')[-1]
                    blob = b.get_blob(f"{ext}/{f['name']}")
                    print(f"{f['name']} -> {blob.generate_signed_url(timedelta(days=1))}")


def remove(client, files):
    b = client.get_bucket(load_config()['bucket'])
    if files[0] == "*":
        for i in b.list_blobs():
            b.get_blob(i.name).delete()
    for target in files:
        for k, v in list_files(client).items():
            for f in v:
                if f['name'] == target:
                    ext = f['name'].split('.')[-1]
                    blob = b.get_blob(f"{ext}/{f['name']}")
                    blob.delete()
                    print(f"Removed {f['name']}")


def list_files(client, filetype=None):
    file_list = {}
    b = client.get_bucket(load_config()['bucket'])

    for i in b.list_blobs():
        ext = i.name.split('/')[0]
        name = i.name.split('/')[1]

        if type(file_list.get(ext, None)) != list:
            file_list[ext] = []

        file_list[ext].append({
            'name': name,
            'created': i.time_created,
            'size': i.size
        })

    if filetype is None:
        return file_list
    else:
        return {f'{filetype}': file_list.get(filetype, [])}


def upload(client, file_path):
    bucket = client.get_bucket(load_config()['bucket'])

    if file_path.__contains__('~'):
        file_path = os.path.expanduser(file_path)

    for i in glob(file_path):
        if os.path.isdir(i):
            continue
        random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        file_suffix = os.path.splitext(i)[1][1::]

        file_name = f"{file_suffix}/{random_id}-{os.path.basename(i)}"
        print(f"Uploading {i} -> gs://{load_config()['bucket']}/{file_name}")
        blob = bucket.blob(file_name)

        blob.upload_from_filename(i)


def main():
    parser = argparse.ArgumentParser(description='Simple Type-organized File Uploader')
    parser.add_argument('path', type=str, nargs='?')

    parser.add_argument('--init', action="store_true", required=False, help="Initializes STFU for use")
    parser.add_argument('--download', '-d', nargs="+", required=False, help="Downloads specified file")
    parser.add_argument('--rm', nargs="+", required=False, help="Remove file")
    parser.add_argument('--share', nargs="+", required=False, help='Create shareable link to file')
    parser.add_argument('--list', '-l', action='store_true', required=False, help="Lists files in storage")
    parser.add_argument('--type', '-t', default=None, type=str, help='Specifies filetype for --list')
    parser.add_argument('--size', '-s', action='store_true', required=False, help="Shows size when using --list")
    parser.add_argument('--date', '-c', action='store_true', required=False, help="Shows created date when using --list")
    args = parser.parse_args()

    if args.init:
        initialize()

    config = load_config()
    try:
        client = storage.Client.from_service_account_json(config['service-account-json-path'])
    except KeyError:
        initialize()

    if args.path is None:
        if args.list is False and args.rm is None and args.download is None and args.share is None:
            exit(0)

    if args.list:
        format_list(list_files(client, filetype=args.type), size=args.size, date=args.date)
    elif args.download is not None:
        download(client, args.download)
    elif args.rm is not None:
        remove(client, args.rm)
    elif args.share is not None:
        share_file(client, args.share)
    elif args.path is not None:
        upload(client, args.path)


if __name__ == '__main__':
    main()
