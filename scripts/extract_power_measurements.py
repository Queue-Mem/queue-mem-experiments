import argparse
import csv
import os
from datetime import datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', required=True)
    parser.add_argument('--output_file', required=True)

    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    input_file_path = os.path.abspath(args.input_file)
    print(f"Reading {input_file_path}...")

    data = []
    with open(input_file_path, "r") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        for row in reader:
            data.append({
                'time': datetime.strptime(row['DateTime (Local Time)'], '%m/%d/%Y %I:%M:%S %p'),
                'total': int(row['Active Energy Import Total'])
            })

    for i in range(1, len(data)):
        time_diff = data[i]['time'] - data[i - 1]['time']
        kwh_diff = data[i]['total'] - data[i - 1]['total']

        data[i]['timedelta'] = time_diff
        data[i]['kwh_diff'] = kwh_diff
        data[i]['usage'] = kwh_diff / (time_diff.total_seconds() / 3600)

    output_file_path = os.path.abspath(args.output_file)
    print(f"Writing results in {output_file_path}...")

    with open(output_file_path, 'w') as output_csv:
        writer = csv.DictWriter(
            output_csv, delimiter=';', fieldnames=['time', 'timedelta', 'total', 'kwh_diff', 'usage']
        )
        writer.writeheader()
        for row in data[1:]:
            writer.writerow(row)


if __name__ == "__main__":
    main(parse_args())
