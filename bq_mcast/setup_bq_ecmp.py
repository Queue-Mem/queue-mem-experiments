import os
import logging
import sys
import time
import statistics
import math
import threading
import random

p4 = bfrt.bq_ecmp

PORTS = [
    16, 24,
    60, 44, 36, 28, 20, 12, 4,
    128, 136, 144, 152, 176, 184, 148
]

# Pipes where the program is running (derived from the input/output ports)
def dev_port_pipe(dev_port):
    return dev_port >> 7

PIPE_NUMS = set(map(dev_port_pipe, PORTS))
print(f"Program running on pipes={PIPE_NUMS}.")


def run_pd_rpc(cmd_or_code, no_print=False):
    """
    This function invokes run_pd_rpc.py tool. It has a single string argument
    cmd_or_code that works as follows:
       If it is a string:
            * if the string starts with os.sep, then it is a filename
            * otherwise it is a piece of code (passed via "--eval"
       Else it is a list/tuple and it is passed "as-is"

    Note: do not attempt to run the tool in the interactive mode!
    """
    import subprocess

    path = os.path.join("/home", "tofino", "tools", "run_pd_rpc.py")

    command = [path]
    if isinstance(cmd_or_code, str):
        if cmd_or_code.startswith(os.sep):
            command.extend(["--no-wait", cmd_or_code])
        else:
            command.extend(["--no-wait", "--eval", cmd_or_code])
    else:
        command.extend(cmd_or_code)

    result = subprocess.check_output(command).decode("utf-8")[:-1]
    if not no_print:
        print(result)

    return result


#################################
########### PORT SETUP ##########
#################################
# In this section, we setup the ports.
def setup_ports():
    global PORTS

    for p in PORTS:
        print("Setting Output Port: %d" % p)
        bfrt.port.port.add(DEV_PORT=p, SPEED='BF_SPEED_100G', FEC='BF_FEC_TYP_REED_SOLOMON', PORT_ENABLE=True)


#################################
############# TABLES ############
#################################
# In this section, we setup the tables.
def setup_tables():
    global p4, PORTS, dev_port_pipe

    mcast_group_ports = PORTS[2:]

    ecmp_profile = p4.pipe.Ingress.ecmp_profile
    ecmp_sel = p4.pipe.Ingress.ecmp_sel
    ecmp_table = p4.pipe.Ingress.ecmp
    ecmp_profile.clear()
    ecmp_sel.clear()
    ecmp_table.clear()

    port_profiles = []
    idx = 0
    for port in mcast_group_ports:
        print(f"Adding ECMP entry for port={port}...")

        ecmp_profile.add_with_to_port(ACTION_MEMBER_ID=idx, eg_port=port)
        port_profiles.append(idx)
        idx += 1

    n_entries = len(port_profiles)
    ecmp_sel.entry(
        SELECTOR_GROUP_ID=1,
        MAX_GROUP_SIZE=n_entries,
        ACTION_MEMBER_ID=port_profiles,
        ACTION_MEMBER_STATUS=[True] * n_entries
    ).push()

    ecmp_table.add(use_ecmp=1, SELECTOR_GROUP_ID=1)

    port_map_table = p4.pipe.Ingress.port_map
    port_map_table.clear()

    for port in mcast_group_ports:
        port_map_table.add_with_to_port(
            ingress_port=port, eg_port=24
        )


########################
######### STATS ########
########################
# This section creates a timer that calls a callback to dump and print stats.
start_ts = time.time()
stats_time = 0

previous_stats = {
    port: {
        'received_pkts_count': 0,
        'received_bytes_count': 0,
        'sent_pkts_count': 0,
        'sent_bytes_count': 0
    } for port in PORTS[2:]
}


def get_stats():
    global logging, time, statistics, bfrt, p4, previous_stats, \
        start_ts, stats_time, PORTS, PIPE_NUMS

    port_stats = bfrt.port.port_stat.get(regex=True, print_ents=False, from_hw=True)

    mcast_ports_stats = filter(
        lambda x: x.key[b'$DEV_PORT'] in PORTS[2:],
        port_stats
    )

    current_stats = {}
    for port_stat in mcast_ports_stats:
        current_stats[port_stat.key[b'$DEV_PORT']] = {
            'received_pkts_count': port_stat.data[b'$FramesReceivedOK'],
            'received_bytes_count': port_stat.data[b'$OctetsReceived'],
            'sent_pkts_count': port_stat.data[b'$FramesTransmittedOK'],
            'sent_bytes_count': port_stat.data[b'$OctetsTransmittedTotal']
        }

    ts = time.time()

    new_stats_time = time.time()
    total_delta_recv_bytes = 0
    total_delta_recv_pkts = 0
    total_delta_sent_pkts = 0
    total_delta_sent_bytes = 0

    for port, port_stat in current_stats.items():
        prev_port_stat = previous_stats[port]
        time_delta = new_stats_time - stats_time

        delta_recv_pkts = (port_stat['received_pkts_count'] - prev_port_stat['received_pkts_count']) / time_delta
        delta_recv_pkts = delta_recv_pkts if delta_recv_pkts > 0 else 0
        total_delta_recv_pkts += delta_recv_pkts

        delta_recv_bytes = (port_stat['received_bytes_count'] - prev_port_stat['received_bytes_count']) / time_delta
        delta_recv_bytes = (delta_recv_bytes * 8) if delta_recv_bytes > 0 else 0
        total_delta_recv_bytes += delta_recv_bytes

        delta_sent_pkts = (port_stat['sent_pkts_count'] - prev_port_stat['sent_pkts_count']) / time_delta
        delta_sent_pkts = delta_sent_pkts if delta_sent_pkts > 0 else 0
        total_delta_sent_pkts += delta_sent_pkts

        delta_sent_bytes = (port_stat['sent_bytes_count'] - prev_port_stat['sent_bytes_count']) / time_delta
        delta_sent_bytes = (delta_sent_bytes * 8) if delta_sent_bytes > 0 else 0
        total_delta_sent_bytes += delta_sent_bytes

    logging.info("MCAST-%f-RESULT-MC_RCV_BPS %f bps" % (ts, total_delta_recv_bytes))
    logging.info("MCAST-%f-RESULT-MC_RCV_PPS %f pps" % (ts, total_delta_recv_pkts))
    logging.info("MCAST-%f-RESULT-MC_SENT_BPS %f bps" % (ts, total_delta_sent_bytes))
    logging.info("MCAST-%f-RESULT-MC_SENT_PPS %f pps" % (ts, total_delta_sent_pkts))
    logging.info("=====================================================================")

    previous_stats = current_stats
    stats_time = new_stats_time


def get_stats_timer():
    import threading

    global get_stats_timer, get_stats
    get_stats()
    threading.Timer(1, get_stats_timer).start()


lab_path = os.path.dirname(__file__)

# Setup Logging
logging.basicConfig(
    format='%(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

(year, month, day, hour, minutes, _, _, _, _) = time.localtime(time.time())
log_path = os.path.join(lab_path, "logs")
log_timestamped_name = '32p-log-%d-%s-%s_%s-%s' % (
    year, str(month).zfill(2), str(day).zfill(2), str(hour).zfill(2), str(minutes).zfill(2)
)
os.makedirs(log_path, exist_ok=True)
file_handler = logging.FileHandler(os.path.join(log_path, "%s.log" % log_timestamped_name))
file_handler.setFormatter(logging.Formatter('%(message)s'))
logging.root.addHandler(file_handler)

setup_ports()
setup_tables()

bfrt.complete_operations()

run_pd_rpc(os.path.join(lab_path, "setup_tm.py"))

stats_time = time.time()
get_stats_timer()
