import logging
import os
import sys
import json
import time

from trex.astf.trex_astf_client import ASTFClient
from trex.astf.trex_astf_exceptions import ASTFError

logging.basicConfig(level=logging.INFO)

SERVER_IP = "127.0.0.1"
DURATION = 30

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: start_trex_server.py <trace> <result_path>")
        exit(1)

    profile_name = sys.argv[1]
    result_path = sys.argv[2]

    logging.info(f"Connecting to trex server: {SERVER_IP}")
    c = ASTFClient(server=SERVER_IP)
    c.connect()

    try:
        c.reset()

        profile_path = profile_name
        
        logging.info(f"Loading profile: {profile_path}")
        c.load_profile(profile_path)

        logging.info(f"Starting traffic...")
        c.start(mult=1, duration=-1)

        start_time = time.time()
        stats_history = {}

        while True:
            elapsed = time.time() - start_time
            stats_history[time.time()] = c.get_stats()

            if elapsed >= DURATION or not c.is_traffic_active():
                break

            time.sleep(1)

        c.stop()

        with open(result_path, "w") as f:
            f.write(json.dumps(stats_history, indent=4))
    except ASTFError as e:
        print(e)
    finally:
        logging.info(f"Disconnecting from trex server...")
        c.disconnect()