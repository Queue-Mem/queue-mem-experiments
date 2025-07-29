import os
import logging
import sys
import time
import statistics
import math
import threading
import random

p4 = bfrt.bq_forwarder

N_MULTICAST = 14

PER_PORT_STATS = False

# If set, only drop tail headers
DROP_TAIL_HEADERS = 0
# If set, only 1/DROP_THRESHOLD packets are sent out the switch
DROP_THRESHOLD = 0
# If set, sends the packets to an external receiver for checking reordering
REORDERING_MEASUREMENT = 0

# Experiment flags
MAX_RATE = False
INCREMENTAL_RATE = False
PEAK_RATE = False
RANDOM_RATE = False
SELECTED_RATE = False
IN_EXPERIMENT = MAX_RATE or INCREMENTAL_RATE or PEAK_RATE or RANDOM_RATE or SELECTED_RATE

PORTS = [
    52, 32, 140, # Traffic Gen + NF Ports
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

    mcast_group_ports = PORTS[3:]

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


#################################
######## TRAFFIC GENERATOR ######
#################################
# In this section, we setup the traffic generator parameters (in registers).
N_PER_FLOW_PKTS = 2


def set_generator():
    global p4, N_PER_FLOW_PKTS

    p4.pipe.Ingress.base_flow_ip.mod(f1=0x01000001, REGISTER_INDEX=0)
    p4.pipe.Ingress.base_flow_ip_index.mod(f1=0, REGISTER_INDEX=0)
    p4.pipe.Ingress.number_of_ip.mod(f1=65535, REGISTER_INDEX=0)
    p4.pipe.Ingress.n_packets_per_flow.mod(f1=N_PER_FLOW_PKTS, REGISTER_INDEX=0)
    p4.pipe.Ingress.flow_packet_counter.mod(f1=1, REGISTER_INDEX=0)
    p4.pipe.Ingress.base_port_flow.mod(f1=1, REGISTER_INDEX=0)
    p4.pipe.Ingress.port_flow.mod(f1=0, REGISTER_INDEX=0)
    p4.pipe.Ingress.max_port.mod(f1=65535, REGISTER_INDEX=0)
    p4.pipe.Ingress.consecutive_flows_number.mod(f1=125, REGISTER_INDEX=0)
    p4.pipe.Ingress.flows_repetition.mod(f1=4, REGISTER_INDEX=0)
    p4.pipe.Ingress.flows_repetition_index.mod(f1=1, REGISTER_INDEX=0)


def set_generator_slf():
    global p4
    TOTAL_PKTS_PER_FLOW = 20
    SLF = 2
    FLOW_REPETITIONS = int(TOTAL_PKTS_PER_FLOW / SLF)
    CONSECUTIVE_FLOWS = 125

    p4.pipe.Ingress.base_flow_ip.mod(f1=0x01000001, REGISTER_INDEX=0)
    p4.pipe.Ingress.base_flow_ip_index.mod(f1=0, REGISTER_INDEX=0)
    p4.pipe.Ingress.number_of_ip.mod(f1=65535, REGISTER_INDEX=0)
    p4.pipe.Ingress.n_packets_per_flow.mod(f1=SLF, REGISTER_INDEX=0)
    p4.pipe.Ingress.flow_packet_counter.mod(f1=1, REGISTER_INDEX=0)
    p4.pipe.Ingress.base_port_flow.mod(f1=1, REGISTER_INDEX=0)
    p4.pipe.Ingress.port_flow.mod(f1=0, REGISTER_INDEX=0)
    p4.pipe.Ingress.max_port.mod(f1=65535, REGISTER_INDEX=0)
    p4.pipe.Ingress.consecutive_flows_number.mod(f1=CONSECUTIVE_FLOWS, REGISTER_INDEX=0)
    p4.pipe.Ingress.flows_repetition.mod(f1=FLOW_REPETITIONS, REGISTER_INDEX=0)
    p4.pipe.Ingress.flows_repetition_index.mod(f1=1, REGISTER_INDEX=0)


######################################
######### VARIABLE RATE ##############
######################################
import random

random.seed(10)
drop_mask_unit = int(36719 / 100)

rates = [drop_mask_unit * 90, drop_mask_unit * 80, drop_mask_unit * 70, drop_mask_unit * 60, drop_mask_unit * 50,
         drop_mask_unit * 40, drop_mask_unit * 30, drop_mask_unit * 20, drop_mask_unit * 10, 0]

random_rates = [
    drop_mask_unit * 90,
    drop_mask_unit * 80,
    drop_mask_unit * 70,
    drop_mask_unit * 60,
    drop_mask_unit * 50,
    drop_mask_unit * 40,
    drop_mask_unit * 30,
    drop_mask_unit * 20, drop_mask_unit * 20, drop_mask_unit * 20,
    drop_mask_unit * 20, drop_mask_unit * 20, drop_mask_unit * 20,
    drop_mask_unit * 10, drop_mask_unit * 10, drop_mask_unit * 10, drop_mask_unit * 10,
    0, 0, 0, 0, 0, 0, 0,
]

random.shuffle(random_rates)


def set_drop_mask(port, mask):
    global drop_mask_unit
    p4.pipe.Egress.drop_mask_reg.mod(REGISTER_INDEX=port, f1=mask)


rate_index = 0


def set_incremental_rate():
    global set_drop_mask, rates, rate_index, PORTS

    for port in range(0, len(PORTS[3:])):
        set_drop_mask(port, rates[rate_index])

    if rate_index == 9:
        rate_index = 9
    else:
        rate_index += 1


def incremental_rate_timer():
    global threading, incremental_rate_timer, set_incremental_rate
    set_incremental_rate()
    threading.Timer(3, incremental_rate_timer).start()


def set_peak_rate():
    global set_drop_mask, rates, rate_index, PORTS

    for port in range(0, len(PORTS[3:])):
        set_drop_mask(port, rates[rate_index])

    if rate_index == 9:
        rate_index = 0
    else:
        rate_index = 9


def peak_rate_timer():
    global threading, peak_rate_timer, set_peak_rate
    set_peak_rate()
    threading.Timer(5, peak_rate_timer).start()


def random_rate_timer():
    global threading, random_rate_timer, set_drop_mask, random_rates, PORTS

    for port in range(0, len(PORTS[3:])):
        set_drop_mask(port, random.choice(random_rates))

    threading.Timer(3, random_rate_timer).start()


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
    } for port in PORTS[3:]
}


def percentile(data, perc):
    global math

    size = len(data)
    return sorted(data)[int(math.ceil((size * perc) / 100)) - 1]


def get_stats():
    global logging, time, statistics, bfrt, p4, percentile, previous_stats, \
        start_ts, stats_time, PORTS, PIPE_NUMS, PER_PORT_STATS

    port_stats = bfrt.port.port_stat.get(regex=True, print_ents=False, from_hw=True)

    mcast_ports_stats = filter(
        lambda x: x.key[b'$DEV_PORT'] in PORTS[3:],
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

    lat_measure_pipe = []
    for pipe_num in PIPE_NUMS:
        lat_measure = p4.pipe.Ingress.latency_measurements.get(
            regex=True, print_ents=False, from_hw=True, pipe=pipe_num
        )
        lat_measure_f = list(
            filter(lambda x: x != 0, map(lambda x: x.data[b'Ingress.latency_measurements.f1'][0], lat_measure))
        )
        lat_measure_f_len = len(lat_measure_f)
        lat_measure_pipe.append(
            (sum(lat_measure_f) / len(lat_measure_f)) / 1000 if len(lat_measure) == lat_measure_f_len else 0
        )

    ts = time.time()

    logging.info("=====================================================================")
    logging.info("MCAST-%f-RESULT-AVG_LATENCY %f us" % (ts, statistics.mean(lat_measure_pipe)))
    logging.info("MCAST-%f-RESULT-99_LATENCY %f us" % (ts, percentile(lat_measure_pipe, 99)))

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

        if PER_PORT_STATS:
            logging.info("MCAST-%f-RESULT-MC_RCV_BPS_PORT%d %f bps" % (ts, port, delta_recv_bytes))
            logging.info("MCAST-%f-RESULT-MC_RCV_PPS_PORT%d %f pps" % (ts, port, delta_recv_pkts))
            logging.info("MCAST-%f-RESULT-MC_SENT_BPS_PORT%d %f bps" % (ts, port, delta_sent_bytes))
            logging.info("MCAST-%f-RESULT-MC_SENT_PPS_PORT%d %f pps" % (ts, port, delta_sent_pkts))

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


def kill_all():
    global os
    os.system("killall -9 run_switchd.sh; killall -9 run_bfshell.sh; killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'")


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

if not REORDERING_MEASUREMENT:
    set_generator()
else:
    set_generator_slf()

p4.pipe.Ingress.drop_tail_headers.mod(f1=DROP_TAIL_HEADERS, REGISTER_INDEX=0)
p4.pipe.Ingress.drop_threshold.mod(f1=DROP_THRESHOLD, REGISTER_INDEX=0)
p4.pipe.Ingress.reordering_measurement.mod(f1=REORDERING_MEASUREMENT, REGISTER_INDEX=0)

bfrt.complete_operations()

run_pd_rpc(os.path.join(lab_path, "setup_tm.py"))

if IN_EXPERIMENT:
    if int(MAX_RATE) + int(INCREMENTAL_RATE) + int(PEAK_RATE) + int(RANDOM_RATE) + int(SELECTED_RATE) > 1:
        print("[ERROR] More than one experiment enabled, killing...")
        kill_all()

    print("Waiting testbed startup...")
    time.sleep(30)

stats_time = time.time()
get_stats_timer()

if INCREMENTAL_RATE:
    p4.pipe.Egress.variable_drop_enabled.mod(f1=1, REGISTER_INDEX=0)
    incremental_rate_timer()

if PEAK_RATE:
    p4.pipe.Egress.variable_drop_enabled.mod(f1=1, REGISTER_INDEX=0)
    rate_index = 9
    peak_rate_timer()

if RANDOM_RATE:
    p4.pipe.Egress.variable_drop_enabled.mod(f1=1, REGISTER_INDEX=0)
    random_rate_timer()

if SELECTED_RATE:
    RATE_SELECTED = 0
    p4.pipe.Egress.variable_drop_enabled.mod(f1=1, REGISTER_INDEX=0)
    for port in range(0, len(PORTS[3:])):
        set_drop_mask(port, rates[RATE_SELECTED])

if IN_EXPERIMENT:
    print("Starting packet generator...")
    run_pd_rpc(os.path.join(lab_path, 'pktgen_start_1500.py'))

    if MAX_RATE:
        time.sleep(20)

    if INCREMENTAL_RATE:
        time.sleep(65)

    if PEAK_RATE:
        time.sleep(40)

    if RANDOM_RATE:
        time.sleep(40)

    if SELECTED_RATE:
        time.sleep(20)

    print("Stopping Experiment...")
    run_pd_rpc(os.path.join(lab_path, 'pktgen_stop.py'))
    kill_all()
