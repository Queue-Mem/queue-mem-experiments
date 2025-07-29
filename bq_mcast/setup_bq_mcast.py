import os
import logging
import sys
import time
import statistics
import math

p4 = bfrt.bq_mcast

# Experiment flags
PRINT_TPUT = True
PRINT_LATENCY = False
PRINT_PER_TYPE_TP = False

N_MULTICAST = 14

# If set, only 1/DROP_THRESHOLD packets are sent out the switch
DROP_THRESHOLD = 0

PORTS = [
    52, # Traffic Gen Port
    32, 140, # NF Ports
    0, # BG Traffic Port (iperf Client)
    60, 44, 36, 28, 20, 12, 4,
    128, 136, 144, 152, 176, 184, 148
]

# Pipes where the program is running (derived from the ports)
PIPE_NUMS = set(map(lambda x: x >> 7, PORTS))
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
######## MULTICAST GROUPS #######
#################################
# In this section, we setup the multicast group.
def setup_multicast():
    global p4, PORTS, N_MULTICAST

    mcast_group_ports = PORTS[4:]

    bfrt.pre.node.entry(MULTICAST_NODE_ID=1, MULTICAST_RID=0xffff,
                        MULTICAST_LAG_ID=[], DEV_PORT=mcast_group_ports).push()

    bfrt.pre.mgid.entry(MGID=100,
                        MULTICAST_NODE_ID=[1],
                        MULTICAST_NODE_L1_XID_VALID=[False],
                        MULTICAST_NODE_L1_XID=[0]).push()

    print(f"Created Multicast Group with ID=100 and ports={mcast_group_ports}...")

    for idx, forwarding_port in enumerate(mcast_group_ports):
        except_ports = mcast_group_ports[(idx + 1):]
        bfrt.pre.prune.entry(MULTICAST_L2_XID=idx + 1, DEV_PORT=except_ports).push()

        print(f"Setting pruning group with multicast_l2_xid={idx + 1} and ports={except_ports}...")

    p4.pipe.Ingress.mcast_xid.mod(REGISTER_INDEX=0, f1=(N_MULTICAST if N_MULTICAST > 0 else 1))


########################
######### STATS ########
########################
# This section creates a timer that calls a callback to dump and print stats.
start_ts = time.time()
stats_time = 0

previous_received_pkts_count = 0
previous_received_bytes_count = 0
previous_sent_pkts_count = 0
previous_sent_bytes_count = 0

previous_bg_bits = 0
previous_not_split_bits = 0
previous_split_bits = 0


def percentile(data, perc):
    global math

    size = len(data)
    return sorted(data)[int(math.ceil((size * perc) / 100)) - 1]


def port_stats():
    global logging, time, statistics, bfrt, p4, percentile, \
        previous_received_pkts_count, previous_received_bytes_count, previous_sent_pkts_count, previous_sent_bytes_count, \
        previous_bg_bits, previous_not_split_bits, previous_split_bits, \
        start_ts, stats_time, PORTS, PIPE_NUMS, PRINT_TPUT, PRINT_LATENCY, PRINT_PER_TYPE_TP

    port_stats = bfrt.port.port_stat.get(regex=True, print_ents=False, from_hw=True)

    mcast_ports_stats = filter(
        lambda x: x.key[b'$DEV_PORT'] in PORTS[4:],
        port_stats
    )

    if PRINT_TPUT:
        total_pkts_received = 0
        total_bytes_received = 0
        total_pkts_sent = 0
        total_bytes_sent = 0
        for port_stat in mcast_ports_stats:
            total_pkts_received += port_stat.data[b'$FramesReceivedOK']
            total_bytes_received += port_stat.data[b'$OctetsReceived']
            total_pkts_sent += port_stat.data[b'$FramesTransmittedOK']
            total_bytes_sent += port_stat.data[b'$OctetsTransmittedTotal']

    if PRINT_LATENCY:
        lat_nf_measure_pipe = []
        for pipe_num in PIPE_NUMS:
            lat_nf_measure = p4.pipe.Ingress.nf_latency_measurements.get(
                regex=True, print_ents=False, from_hw=True, pipe=pipe_num
            )
            lat_nf_measure_f = list(
                filter(lambda x: x != 0, map(lambda x: x.data[b'Ingress.nf_latency_measurements.f1'][0], lat_nf_measure))
            )
            lat_nf_measure_f_len = len(lat_nf_measure_f)
            lat_nf_measure_pipe.append(
                (sum(lat_nf_measure_f) / len(lat_nf_measure_f)) / 1000 if len(lat_nf_measure) == lat_nf_measure_f_len else 0
            )

        lat_not_split_measure_pipe = []
        for pipe_num in PIPE_NUMS:
            lat_not_split_measure = p4.pipe.Ingress.not_split_latency_measurements.get(
                regex=True, print_ents=False, from_hw=True, pipe=pipe_num
            )
            lat_not_split_measure_f = list(
                filter(lambda x: x != 0, map(lambda x: x.data[b'Ingress.not_split_latency_measurements.f1'][0], lat_not_split_measure))
            )
            lat_not_split_measure_f_len = len(lat_not_split_measure_f)
            lat_not_split_measure_pipe.append(
                (sum(lat_not_split_measure_f) / len(lat_not_split_measure_f)) / 1000 if len(lat_not_split_measure) == lat_not_split_measure_f_len else 0
            )

        lat_bg_measure_pipe = []
        for pipe_num in PIPE_NUMS:
            lat_bg_measure = p4.pipe.Ingress.bg_latency_measurements.get(
                regex=True, print_ents=False, from_hw=True, pipe=pipe_num
            )
            lat_bg_measure_f = list(
                filter(lambda x: x != 0, map(lambda x: x.data[b'Ingress.bg_latency_measurements.f1'][0], lat_bg_measure))
            )
            lat_bg_measure_f_len = len(lat_bg_measure_f)
            lat_bg_measure_pipe.append(
                (sum(lat_bg_measure_f) / len(lat_bg_measure_f)) / 1000 if len(lat_bg_measure) == lat_bg_measure_f_len else 0
            )

    if PRINT_PER_TYPE_TP:
        bg_stats = p4.pipe.Ingress.bg_stats.get(
            COUNTER_INDEX=0, print_ents=False, from_hw=True
        )
        current_bg_bits = bg_stats.data[b'$COUNTER_SPEC_BYTES'] * 8

        not_split_ports_stats = p4.pipe.Ingress.not_split_ports_stats.get(
            COUNTER_INDEX=0, print_ents=False, from_hw=True
        )
        current_not_split_bits = not_split_ports_stats.data[b'$COUNTER_SPEC_BYTES'] * 8

        split_ports_stats = p4.pipe.Ingress.split_ports_stats.get(
            COUNTER_INDEX=0, print_ents=False, from_hw=True
        )
        current_split_bits = split_ports_stats.data[b'$COUNTER_SPEC_BYTES'] * 8

    ts = time.time()

    new_stats_time = time.time()
    time_delta = new_stats_time - stats_time
    if PRINT_TPUT:
        delta_recv_bytes = (total_bytes_received - previous_received_bytes_count) / time_delta
        delta_recv_pkts = (total_pkts_received - previous_received_pkts_count) / time_delta
        delta_sent_bytes = (total_bytes_sent - previous_sent_bytes_count) / time_delta
        delta_sent_pkts = (total_pkts_sent - previous_sent_pkts_count) / time_delta
    if PRINT_PER_TYPE_TP:
        delta_bg = (current_bg_bits - previous_bg_bits) / time_delta
        delta_not_split = (current_not_split_bits - previous_not_split_bits) / time_delta
        delta_split = (current_split_bits - previous_split_bits) / time_delta

    logging.info("=====================================================================")
    if PRINT_LATENCY:
        logging.info("MCAST-%f-RESULT-AVG_LATENCY %f us" % (ts, statistics.mean(lat_nf_measure_pipe)))
        logging.info("MCAST-%f-RESULT-99_LATENCY %f us" % (ts, percentile(lat_nf_measure_pipe, 99)))
        logging.info("MCAST-%f-RESULT-AVG_NOT_SPLIT_LATENCY %f us" % (ts, statistics.mean(lat_not_split_measure_pipe)))
        logging.info("MCAST-%f-RESULT-99_NOT_SPLIT_LATENCY %f us" % (ts, percentile(lat_not_split_measure_pipe, 99)))
        logging.info("MCAST-%f-RESULT-AVG_BG_LATENCY %f us" % (ts, statistics.mean(lat_bg_measure_pipe)))
        logging.info("MCAST-%f-RESULT-99_BG_LATENCY %f us" % (ts, percentile(lat_bg_measure_pipe, 99)))
    if PRINT_TPUT:
        logging.info("MCAST-%f-RESULT-MC_RCV_BPS %f bps" % (ts, delta_recv_bytes * 8))
        logging.info("MCAST-%f-RESULT-MC_RCV_PPS %f pps" % (ts, delta_recv_pkts))
        logging.info("MCAST-%f-RESULT-MC_SENT_BPS %f bps" % (ts, delta_sent_bytes * 8))
        logging.info("MCAST-%f-RESULT-MC_SENT_PPS %f pps" % (ts, delta_sent_pkts))
    if PRINT_PER_TYPE_TP:
        logging.info("MCAST-%f-RESULT-BG_BPS %f bps" % (ts, delta_bg))
        logging.info("MCAST-%f-RESULT-NOT_SPLIT_BPS %f bps" % (ts, delta_not_split))
        logging.info("MCAST-%f-RESULT-SPLIT_BPS %f bps" % (ts, delta_split))
    logging.info("=====================================================================")
    
    if PRINT_PER_TYPE_TP:
        previous_bg_bits = current_bg_bits
        previous_not_split_bits = current_not_split_bits
        previous_split_bits = current_split_bits

    if PRINT_TPUT:
        previous_received_pkts_count = total_pkts_received
        previous_received_bytes_count = total_bytes_received
        previous_sent_pkts_count = total_pkts_sent
        previous_sent_bytes_count = total_bytes_sent

    stats_time = new_stats_time


def port_stats_timer():
    import threading

    global port_stats_timer, port_stats, PRINT_TPUT
    port_stats()
    threading.Timer(0.5 if not PRINT_TPUT else 1, port_stats_timer).start()


###########################
##### BLACKLIST TABLE #####
###########################
# This function setups the entries in the blacklist table.
# You can add/edit/remove entries to disable payload splitting on specific traffic classes.
def setup_blacklist_table():
    from ipaddress import ip_address
    global p4

    blacklist_table = p4.pipe.Ingress.blacklist
    blacklist_table.clear()

    blacklist_table.add_with_drop(dst_addr=ip_address('224.0.0.0'), dst_addr_p_length=16)


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
setup_multicast()
setup_blacklist_table()
p4.pipe.Ingress.drop_threshold.mod(f1=DROP_THRESHOLD, REGISTER_INDEX=0)

bfrt.complete_operations()

run_pd_rpc(os.path.join(lab_path, "setup_tm.py"))

stats_time = time.time()
port_stats_timer()
