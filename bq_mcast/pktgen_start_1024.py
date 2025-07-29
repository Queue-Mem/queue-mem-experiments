from scapy.all import *


# #################################
# ######## PACKET GENERATOR #######
# #################################
def start_traffic():
    p = Ether(dst='00:00:00:00:00:01', src='00:00:00:00:00:00', type=0x0800) / IP(dst="1.2.3.4", src="5.6.7.8", frag=0x0, len=998) / UDP(sport=1234, dport=5678, len=990)
    pktgen.write_pkt_buffer(0, len(p) - 6, bytes(p)[6:])
    pktgen.enable(68)

    app = pktgen.app_cfg_init()
    app.buffer_offset = 0
    app.length = 1024
    app.trigger_type = pktgen.TriggerType_t.TIMER_PERIODIC
    app.timer = 10000
    app.pkt_count = 113

    pktgen.cfg_app(0, app)

    pktgen.app_enable(0)


print("Starting pktgen")
start_traffic()
