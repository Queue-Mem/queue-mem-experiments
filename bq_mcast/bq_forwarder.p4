/* -*- P4_16 -*- */

#include <core.p4>
#include <tna.p4>

#define NF_PORT_PIPE0 32
#define NF_PORT_PIPE1 140
#define PKTGEN_PORT 68
#define RECV_PORT 52

#define N_LAT_MEASUREMENTS 1024

#define N_MULTICAST 14
#define PACKET_PER_UNIT 36719

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

header numberize_h {
    bit<32> pkt_id;
}

header header_info_h {
    bit<32> hdr_idx;
    bit<32> pkt_id;
    bit<8> pkt_type;
}

struct my_ingress_headers_t {
    ethernet_h ethernet;
    ipv4_h ipv4;
    udp_h udp;
    tcp_h tcp;
    numberize_h numberize;
    header_info_h header_info;
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
        transition select(ig_intr_md.ingress_port) {
            NF_PORT_PIPE0: parse_header_info;
            NF_PORT_PIPE1: parse_header_info;
            PKTGEN_PORT: parse_numberize;
            default: accept;
        }
    }

    state parse_udp {
        pkt.extract(hdr.udp);
        transition select(ig_intr_md.ingress_port) {
            NF_PORT_PIPE0: parse_header_info;
            NF_PORT_PIPE1: parse_header_info;
            PKTGEN_PORT: parse_numberize;
            default: accept;
        }
    }

    state parse_numberize {
        pkt.extract(hdr.numberize);
        transition accept;
    }

    state parse_header_info {
        pkt.extract(hdr.header_info);
        transition accept;
    }
}

control Ingress(inout my_ingress_headers_t hdr, inout my_ingress_metadata_t meta,
                in ingress_intrinsic_metadata_t ig_intr_md, in ingress_intrinsic_metadata_from_parser_t ig_prsr_md,
                inout ingress_intrinsic_metadata_for_deparser_t ig_dprsr_md, inout ingress_intrinsic_metadata_for_tm_t ig_tm_md) {
    DirectRegister<bit<16>>() measurement_idx;
    Register<bit<32>, _>(N_LAT_MEASUREMENTS) latency_measurements;

    DirectRegisterAction<bit<16>, bit<16>>(measurement_idx) measurement_idx_increment = {
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
    RegisterAction<bit<32>, _, bit<32>>(latency_measurements) store_latency_measurement = {
        void apply(inout bit<32> value, out bit<32> read_value) {
            value = latency_value;
        }
    };

    Register<bit<16>, _>(1) mcast_xid;

    Register<bit<16>, _>(1) n_packets_per_flow;
    Register<bit<16>, _>(1) base_port_flow;                    
    Register<bit<16>, _>(1) port_flow;
    Register<bit<16>, _>(1) max_port;
    Register<bit<16>, _>(1) flow_packet_counter;
    Register<bit<32>, _>(1) base_flow_ip;
    Register<bit<32>, _>(1) base_flow_ip_index;
    Register<bit<32>, _>(1) number_of_ip;
    Register<bit<16>, _>(1) consecutive_flows_number;
    Register<bit<16>, _>(1) flows_repetition;
    Register<bit<16>, _>(1) flows_repetition_index;
    
    bit<16> repetition;
    bit<16> consecutive_flows_num;

    bit<32> max_number_of_ip;
    bit<16> max_port_value;

    RegisterAction<bit<16>, _, bit<16>>(base_port_flow) base_port_flow_increment = {
        void apply(inout bit<16> value, out bit<16> read_value) {
            if (value == max_port_value) {
                value = 1;
            } else {
                value = value + consecutive_flows_num;
            }
            read_value = value;
        }
    };

    RegisterAction<bit<16>, _, bool>(flows_repetition_index) flows_repetition_index_read_and_increment = {
        void apply(inout bit<16> value, out bool read_value) {
            if (value == repetition) {
                value = 1;
                read_value = false;
            } else {
                value = value + 1;
                read_value = true;
            }
        }
    };

    RegisterAction<bit<16>, _, bit<16>>(port_flow) port_flow_increment = {
        void apply(inout bit<16> value, out bit<16> read_value) {
            if (value == consecutive_flows_num - 1) {
                value = 0;
            } else {
                value = value + 1;
            }
            read_value = value;
        }
    };

    bit<16> pkts_per_flow;
    RegisterAction<bit<16>, _, bool>(flow_packet_counter) flow_packet_counter_increment = {
        void apply(inout bit<16> value, out bool read_value) {
            if (value == pkts_per_flow) {
                value = 1;
                read_value = true;
            } else {
                value = value + 1;
                read_value = false;
            }
        }
    };

    RegisterAction<bit<32>, _, bit<32>>(base_flow_ip_index) base_flow_ip_index_increment = {
        void apply(inout bit<32> value, out bit<32> read_value) {
            if (value == max_number_of_ip) {
                value = 0;
            } else {
                value = value + 1;
            }
            read_value = value;
        }
    };

    Random<bit<32>>() src_ip_gen;
    bit<32> src_ip_seed = src_ip_gen.get();
    RegisterAction<bit<32>, _, bit<32>>(base_flow_ip) base_flow_ip_update = {
        void apply(inout bit<32> value, out bit<32> read_value) {
            value = src_ip_seed;
            read_value = value;
        }
    };

    Register<bit<32>, _>(1) drop_tail_headers;
    RegisterAction<bit<32>, _, bit<32>>(drop_tail_headers) drop_tail_headers_read = {
        void apply(inout bit<32> value, out bit<32> read_value) {
            read_value = value;
        }
    };

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

    Register<bit<8>, _>(1) reordering_measurement;
    RegisterAction<bit<8>, _, bit<8>>(reordering_measurement) reordering_measurement_read = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            read_value = value;
        }
    };

    Register<bit<32>, _>(1) pkt_num;
    RegisterAction<bit<32>, _, bit<32>>(pkt_num) pkt_num_inc = {
        void apply(inout bit<32> value, out bit<32> read_value) {
            read_value = value;
            value = value + 1;
        }
    };

    apply {
        if (hdr.ipv4.isValid()) {
            if (ig_intr_md.ingress_port == PKTGEN_PORT) {
                /* Tag the packet with the ingress timestamp */
                hdr.ethernet.dst_addr[47:16] = ig_prsr_md.global_tstamp[31:0];

                ig_tm_md.mcast_grp_a = 100;
                ig_tm_md.rid = 0xffff;
                ig_tm_md.level2_exclusion_id = (bit<9>) mcast_xid.read(0);

                pkts_per_flow = n_packets_per_flow.read(0);
                consecutive_flows_num = consecutive_flows_number.read(0);
                repetition = flows_repetition.read(0);
                max_number_of_ip = number_of_ip.read(0);
                
                bit<16> base_port_flow_value;
                bit<16> port_flow_value;
                bit<32> base_ip_value;
                bit<32> ip_index_value;
                bool to_repeat = true;
                bool flow_packet_counter_value = flow_packet_counter_increment.execute(0);

                if (flow_packet_counter_value) {
                    max_port_value = max_port.read(0);
                    port_flow_value = port_flow_increment.execute(0);
                    if (port_flow_value == 0) {
                        to_repeat = flows_repetition_index_read_and_increment.execute(0);
                    }

                    if (to_repeat) {
                        base_port_flow_value = base_port_flow.read(0);
                    } else {
                        base_port_flow_value = base_port_flow_increment.execute(0);
                    }
                    
                    if (port_flow_value == 0 && !to_repeat) {
                        base_ip_value = base_flow_ip_update.execute(0);
                        ip_index_value = base_flow_ip_index_increment.execute(0);
                    } else {
                        base_ip_value = base_flow_ip.read(0);
                        ip_index_value = base_flow_ip_index.read(0);
                    }
                } else {
                    base_ip_value = base_flow_ip.read(0);
                    ip_index_value = base_flow_ip_index.read(0);
                    base_port_flow_value = base_port_flow.read(0);
                    port_flow_value = port_flow.read(0);
                }

                hdr.ipv4.src_addr = base_ip_value;
                hdr.ipv4.dst_addr = base_ip_value + ip_index_value;
                hdr.udp.src_port = 1000;
                hdr.udp.dst_port = base_port_flow_value + port_flow_value;

                hdr.numberize.pkt_id = pkt_num_inc.execute(0);
            } else if (ig_intr_md.ingress_port == NF_PORT_PIPE0 || ig_intr_md.ingress_port == NF_PORT_PIPE1) {
                mac_addr_t src = hdr.ethernet.src_addr;

                hdr.ethernet.src_addr = hdr.ethernet.dst_addr;
                hdr.ethernet.dst_addr = src;

                ig_tm_md.ucast_egress_port = ig_intr_md.ingress_port;
                ig_tm_md.bypass_egress = 0x1;

                bit<32> drop_tail_hdr = drop_tail_headers_read.execute(0);
                if ((drop_tail_hdr == 1 && hdr.header_info.pkt_type == 0xcc) || drop_tail_hdr == 0) {
                    drop_thresh = drop_threshold_read.execute(0);
                    if (drop_thresh != 0) {
                        ig_dprsr_md.drop_ctl = (bit<3>) drop_counter_increment.execute(0);
                    }
                }
            } else {
                bit<1> will_drop = 1;
                if (hdr.udp.src_port == 1000) {
                    /* Compute the latency on original packets */
                    bit<16> idx = measurement_idx_increment.execute();
                    latency_value = ig_prsr_md.global_tstamp[31:0] - hdr.ethernet.src_addr[47:16];
                    store_latency_measurement.execute(idx);

                    /* If we are measuring reordering, send the packet to the external receiver */
                    bit<8> measure_reordering = reordering_measurement_read.execute(0);
                    if (measure_reordering == 1) {
                        ig_tm_md.ucast_egress_port = RECV_PORT;
                        ig_tm_md.bypass_egress = 0x1;
                        will_drop = 0;
                    }
                }

                if (will_drop == 1) {
                    ig_dprsr_md.drop_ctl = 0x1;
                }
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

struct forward_packet_t {
    bit<16> to_forward;
    bit<16> to_drop;
}

control Egress(inout my_egress_headers_t hdr, inout my_egress_metadata_t meta,
               in egress_intrinsic_metadata_t eg_intr_md, in egress_intrinsic_metadata_from_parser_t eg_prsr_md,
               inout egress_intrinsic_metadata_for_deparser_t eg_dprsr_md, inout egress_intrinsic_metadata_for_output_port_t eg_oport_md) {
    Register<bit<1>, _>(1) variable_drop_enabled;
    Register<bit<16>, _>(N_MULTICAST) drop_mask_reg;
    Register<forward_packet_t, _>(N_MULTICAST) forward_packet;
    
    bit<1> variable_drop = 0;
    bit<16> drop_mask = 0;
    RegisterAction<forward_packet_t, _, bit<3>>(forward_packet) forward_packet_update = {
        void apply(inout forward_packet_t value, out bit<3> read_value) {
            if (value.to_drop == 0) {
                if (value.to_forward == 0) {
                    value.to_drop = drop_mask;
                    value.to_forward = PACKET_PER_UNIT - drop_mask;
                    read_value = 0x1;
                } else {
                    value.to_forward = value.to_forward - 1;
                    read_value = 0x0;
                }
            } else {
                value.to_drop = value.to_drop - 1;
                read_value = 0x1;
            }
        }
    };
    
    bit<16> reg_idx = 0;
    action assign_idx(bit<16> idx) {
        hdr.ipv4.src_addr = hdr.ipv4.src_addr + (bit<32>) idx;
        hdr.ipv4.dst_addr = hdr.ipv4.dst_addr + (bit<32>) idx;
        hdr.udp.src_port = hdr.udp.src_port + idx;
        hdr.udp.dst_port = hdr.udp.dst_port + idx;
        reg_idx = idx;
    }

    @ternary(1)
    table port_to_idx {
        key = {
            eg_intr_md.egress_port: exact;
        }
        actions = {
            assign_idx;
        }
        size = N_MULTICAST;
        const entries = {
            60: assign_idx(0);
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

            variable_drop = variable_drop_enabled.read(0);
            if (variable_drop == 1) {
                drop_mask = drop_mask_reg.read(reg_idx);
                eg_dprsr_md.drop_ctl = forward_packet_update.execute(reg_idx);
            }
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
