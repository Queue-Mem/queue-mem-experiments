/* -*- P4_16 -*- */

#include <core.p4>
#include <tna.p4>

#define NF_PORT_PIPE0 32
#define NF_PORT_PIPE1 140
#define TRAFFIC_GEN_PORT 52
#define BG_TRAFFIC_PORT 0

#define N_LAT_MEASUREMENTS 1024

/* INGRESS */
/* Types */
enum bit<16> ether_type_t {
    IPV4 = 0x0800
}

/* IPv4 protocol type */
enum bit<8> ipv4_protocol_t {
    TCP = 0x06,
    UDP = 0x11
}

typedef bit<48> mac_addr_t;
typedef bit<32> ipv4_addr_t;

/* Standard headers */
header ethernet_h {
    mac_addr_t dst_addr;
    mac_addr_t src_addr;
    ether_type_t ether_type;
}

header ipv4_h {
    bit<4> version;
    bit<4> ihl;
    bit<6> dscp;
    bit<2> ecn;
    bit<16> total_len;
    bit<16> identification;
    bit<3> flags;
    bit<13> frag_offset;
    bit<8> ttl;
    ipv4_protocol_t protocol;
    bit<16> hdr_checksum;
    ipv4_addr_t src_addr;
    ipv4_addr_t dst_addr;
}

header tcp_h {
    bit<16> src_port;
    bit<16> dst_port;
    bit<32> seq_n;
    bit<32> ack_n;
    bit<4> data_offset;
    bit<4> res;
    bit<1> cwr;
    bit<1> ece;
    bit<1> urg;
    bit<1> ack;
    bit<1> psh;
    bit<1> rst;
    bit<1> syn;
    bit<1> fin;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgent_ptr;
}

header udp_h {
    bit<16> src_port;
    bit<16> dst_port;
    bit<16> length;
    bit<16> checksum;
}

struct my_ingress_headers_t {
    ethernet_h ethernet;
    ipv4_h ipv4;
    udp_h udp;
    tcp_h tcp;
}

struct my_ingress_metadata_t {}

parser IngressParser(packet_in pkt, out my_ingress_headers_t hdr, out my_ingress_metadata_t meta, out ingress_intrinsic_metadata_t ig_intr_md) {
    /* This is a mandatory state, required by Tofino Architecture */
    state start {
        pkt.extract(ig_intr_md);
        pkt.advance(PORT_METADATA_SIZE);
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ether_type_t.IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            ipv4_protocol_t.TCP: parse_tcp;
            ipv4_protocol_t.UDP: parse_udp;
            default: accept;
        }
    }

    state parse_tcp {
        pkt.extract(hdr.tcp);
        transition accept;
    }

    state parse_udp {
        pkt.extract(hdr.udp);
        transition accept;
    }
}

control Ingress(inout my_ingress_headers_t hdr, inout my_ingress_metadata_t meta,
                in ingress_intrinsic_metadata_t ig_intr_md, in ingress_intrinsic_metadata_from_parser_t ig_prsr_md,
                inout ingress_intrinsic_metadata_for_deparser_t ig_dprsr_md, inout ingress_intrinsic_metadata_for_tm_t ig_tm_md) {
    Register<bit<16>, _>(1) nf_measurement_idx;
    Register<bit<16>, _>(1) not_split_measurement_idx;
    Register<bit<16>, _>(1) bg_measurement_idx;
    Register<bit<32>, _>(N_LAT_MEASUREMENTS) nf_latency_measurements;
    Register<bit<32>, _>(N_LAT_MEASUREMENTS) not_split_latency_measurements;
    Register<bit<32>, _>(N_LAT_MEASUREMENTS) bg_latency_measurements;
    Register<bit<16>, _>(1) mcast_xid;

    RegisterAction<bit<16>, _, bit<16>>(nf_measurement_idx) nf_measurement_idx_increment = {
        void apply(inout bit<16> value, out bit<16> read_value) {
            read_value = value;

            if (value == (N_LAT_MEASUREMENTS - 1)) {
                value = 0;
            } else {
                value = value + 1;
            }
        }
    };

    RegisterAction<bit<16>, _, bit<16>>(not_split_measurement_idx) not_split_measurement_idx_increment = {
        void apply(inout bit<16> value, out bit<16> read_value) {
            read_value = value;

            if (value == (N_LAT_MEASUREMENTS - 1)) {
                value = 0;
            } else {
                value = value + 1;
            }
        }
    };

    RegisterAction<bit<16>, _, bit<16>>(bg_measurement_idx) bg_measurement_idx_increment = {
        void apply(inout bit<16> value, out bit<16> read_value) {
            read_value = value;

            if (value == (N_LAT_MEASUREMENTS - 1)) {
                value = 0;
            } else {
                value = value + 1;
            }
        }
    };

    bit<32> latency_value;
    RegisterAction<bit<32>, _, bit<32>>(nf_latency_measurements) store_nf_latency_measurement = {
        void apply(inout bit<32> value, out bit<32> read_value) {
            value = latency_value;
        }
    };

    RegisterAction<bit<32>, _, bit<32>>(not_split_latency_measurements) store_not_split_latency_measurement = {
        void apply(inout bit<32> value, out bit<32> read_value) {
            value = latency_value;
        }
    };

    RegisterAction<bit<32>, _, bit<32>>(bg_latency_measurements) store_bg_latency_measurement = {
        void apply(inout bit<32> value, out bit<32> read_value) {
            value = latency_value;
        }
    };

    action drop() {
        ig_dprsr_md.drop_ctl = 0x1;
    }

    table blacklist {
        key = {
            hdr.ipv4.dst_addr: lpm;
        }
        actions = {
            drop;
        }
        size = 1024;
    }

    action assign_port(PortId_t p) {
        ig_tm_md.ucast_egress_port = p;
    }

    @ternary(1)
    table tcp_dst_to_port {
        key = {
            hdr.tcp.dst_port: exact;
        }
        actions = {
            assign_port;
        }
        size = 14;
        default_action = assign_port(60);
        const entries = {
            5201: assign_port(60);
            5202: assign_port(44);
            5203: assign_port(36);
            5204: assign_port(28);
            5205: assign_port(20);
            5206: assign_port(12);
            5207: assign_port(4);
            5208: assign_port(128);
            5209: assign_port(136);
            5210: assign_port(144);
            5211: assign_port(152);
            5212: assign_port(176);
            5213: assign_port(184);
            5214: assign_port(148);
        }
    }

    Counter<bit<64>, bit<1>>(1, CounterType_t.PACKETS_AND_BYTES) bg_stats;
    Counter<bit<64>, bit<1>>(1, CounterType_t.PACKETS_AND_BYTES) split_ports_stats;
    Counter<bit<64>, bit<1>>(1, CounterType_t.PACKETS_AND_BYTES) not_split_ports_stats;

    Register<bit<32>, _>(1) drop_counter;
    Register<bit<32>, _>(1) drop_threshold;
    bit<32> drop_thresh = 0;
    RegisterAction<bit<32>, _, bit<8>>(drop_counter) drop_counter_increment = {
        void apply(inout bit<32> value, out bit<8> read_value) {
            if (value + 1 == drop_thresh) {
                value = 0;

                read_value = 1;
            } else {
                value = value + 1;
                
                read_value = 0;
            }
        }
    };

    RegisterAction<bit<32>, _, bit<32>>(drop_threshold) drop_threshold_read = {
        void apply(inout bit<32> value, out bit<32> read_value) {
            read_value = value;
        }
    };

    apply {
        if (hdr.ipv4.isValid()) {
            bit<1> count_bg = 0;

            if (ig_intr_md.ingress_port == TRAFFIC_GEN_PORT) {
                if (!blacklist.apply().hit) {
                    /* Tag the packet with the ingress timestamp */
                    hdr.ethernet.dst_addr[47:16] = ig_prsr_md.global_tstamp[31:0];

                    ig_tm_md.mcast_grp_a = 100;
                    ig_tm_md.rid = 0xffff;
                    ig_tm_md.level2_exclusion_id = (bit<9>) mcast_xid.read(0);
                }
            } else if (ig_intr_md.ingress_port == BG_TRAFFIC_PORT) {
                /* Assign one of the multicast ports based on the src IP */
                tcp_dst_to_port.apply();

                ig_tm_md.bypass_egress = 0x1;

                count_bg = 1;
            } else if (ig_intr_md.ingress_port == NF_PORT_PIPE0 || ig_intr_md.ingress_port == NF_PORT_PIPE1) {
                mac_addr_t src = hdr.ethernet.src_addr;

                hdr.ethernet.src_addr = hdr.ethernet.dst_addr;
                hdr.ethernet.dst_addr = src;

                ig_tm_md.ucast_egress_port = ig_intr_md.ingress_port;
                ig_tm_md.bypass_egress = 0x1;

                drop_thresh = drop_threshold_read.execute(0);
                if (drop_thresh != 0) {
                    ig_dprsr_md.drop_ctl = (bit<3>) drop_counter_increment.execute(0);
                }
            } else {
                latency_value = ig_prsr_md.global_tstamp[31:0] - hdr.ethernet.src_addr[47:16];
                bit<1> compute_latency = 1;
                bit<8> pkt_type = hdr.ethernet.dst_addr[7:0];
                if (hdr.ipv4.identification == 0xffff) {
                    hdr.ipv4.identification = 0x0;

                    ig_tm_md.ucast_egress_port = TRAFFIC_GEN_PORT;
                    ig_tm_md.bypass_egress = 0x1;
                } else if (hdr.ipv4.protocol == ipv4_protocol_t.TCP && hdr.ipv4.dst_addr == 0xc0a80487) {
                    ig_tm_md.ucast_egress_port = BG_TRAFFIC_PORT;
                    ig_tm_md.bypass_egress = 0x1;
                } else {
                    ig_dprsr_md.drop_ctl = 0x1;
                
                    compute_latency = 0;
                }

                if (pkt_type == 0x2) {
                    count_bg = 1;
                    
                    if (compute_latency == 1) {
                        bit<16> bg_idx = bg_measurement_idx_increment.execute(0);
                        store_bg_latency_measurement.execute(bg_idx);
                    }
                } else if (pkt_type == 0x0) {
                    not_split_ports_stats.count(0);

                    if (compute_latency == 1) {
                        bit<16> not_split_idx = not_split_measurement_idx_increment.execute(0);
                        store_not_split_latency_measurement.execute(not_split_idx);
                    }
                } else if (pkt_type == 0x1) {
                    split_ports_stats.count(0);

                    if (compute_latency == 1) {
                        bit<16> nf_idx = nf_measurement_idx_increment.execute(0);
                        store_nf_latency_measurement.execute(nf_idx);
                    }
                }
            }
        
            if (count_bg == 1) {
                bg_stats.count(0);
            }
        }
    }
}

control IngressDeparser(packet_out pkt, inout my_ingress_headers_t hdr,
                        in my_ingress_metadata_t meta, in ingress_intrinsic_metadata_for_deparser_t ig_dprsr_md) {
    apply {
        pkt.emit(hdr);
    }
}


/* EGRESS */
struct my_egress_headers_t {
    ethernet_h ethernet;
    ipv4_h ipv4;
    tcp_h tcp;
    udp_h udp;
}

struct my_egress_metadata_t {
}

parser EgressParser(packet_in pkt, out my_egress_headers_t hdr, out my_egress_metadata_t meta,
                    out egress_intrinsic_metadata_t eg_intr_md) {
    /* This is a mandatory state, required by Tofino Architecture */
    state start {
        pkt.extract(eg_intr_md);
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ether_type_t.IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            ipv4_protocol_t.TCP: parse_tcp;
            ipv4_protocol_t.UDP: parse_udp;
            default: accept;
        }
    }

    state parse_tcp {
        pkt.extract(hdr.tcp);
        transition accept;
    }

    state parse_udp {
        pkt.extract(hdr.udp);
        transition accept;
    }
}

control Egress(inout my_egress_headers_t hdr, inout my_egress_metadata_t meta,
               in egress_intrinsic_metadata_t eg_intr_md, in egress_intrinsic_metadata_from_parser_t eg_prsr_md,
               inout egress_intrinsic_metadata_for_deparser_t eg_dprsr_md, inout egress_intrinsic_metadata_for_output_port_t eg_oport_md) {
    action assign_identification() {
        hdr.ipv4.identification = 0xffff;
    }

    action assign_idx(bit<16> idx) {
        hdr.ipv4.src_addr = hdr.ipv4.src_addr + (bit<32>) idx;
        hdr.ipv4.dst_addr = hdr.ipv4.dst_addr + (bit<32>) idx;
        hdr.udp.src_port = hdr.udp.src_port + idx;
        hdr.udp.dst_port = hdr.udp.dst_port + idx;
    }

    @ternary(1)
    table port_to_idx {
        key = {
            eg_intr_md.egress_port: exact;
        }
        actions = {
            assign_idx;
            assign_identification;
        }
        size = 14;
        const entries = {
            60: assign_identification();
            44: assign_idx(1);
            36: assign_idx(2);
            28: assign_idx(3);
            20: assign_idx(4);
            12: assign_idx(5);
            4: assign_idx(6);
            128: assign_idx(7);
            136: assign_idx(8);
            144: assign_idx(9);
            152: assign_idx(10);
            176: assign_idx(11);
            184: assign_idx(12);
            148: assign_idx(13);
        }
    }

    apply {
        if (hdr.ipv4.isValid()) {
            port_to_idx.apply();
        }
    }
}

control EgressDeparser(packet_out pkt, inout my_egress_headers_t hdr, in my_egress_metadata_t meta,
                       in egress_intrinsic_metadata_for_deparser_t  eg_dprsr_md) {
    apply {
        pkt.emit(hdr);
    }
}

Pipeline(
    IngressParser(),
    Ingress(),
    IngressDeparser(),
    EgressParser(),
    Egress(),
    EgressDeparser()
) pipe;

Switch(pipe) main;
