/* -*- P4_16 -*- */

#include <core.p4>
#include <tna.p4>

#define CLIENT_PORT 16
#define SERVER_PORT 24

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

/* Struct to store L4 ports */
struct l4_lookup_t {
    bit<16> src_port;
    bit<16> dst_port;
}

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

struct my_ingress_metadata_t {
    l4_lookup_t l4_lookup;
}

parser IngressParser(packet_in pkt, out my_ingress_headers_t hdr, out my_ingress_metadata_t meta, out ingress_intrinsic_metadata_t ig_intr_md) {
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
        meta.l4_lookup = {hdr.tcp.src_port, hdr.tcp.dst_port};
        transition accept;
    }

    state parse_udp {
        pkt.extract(hdr.udp);
        meta.l4_lookup = {hdr.udp.src_port, hdr.udp.dst_port};
        transition accept;
    }
}

control Ingress(inout my_ingress_headers_t hdr, inout my_ingress_metadata_t meta,
                in ingress_intrinsic_metadata_t ig_intr_md, in ingress_intrinsic_metadata_from_parser_t ig_prsr_md,
                inout ingress_intrinsic_metadata_for_deparser_t ig_dprsr_md, inout ingress_intrinsic_metadata_for_tm_t ig_tm_md) {
    bit<8> use_ecmp = 0;

    Hash<bit<32>>(HashAlgorithm_t.CRC32) ecmp_hash;
    ActionProfile(size=128) ecmp_profile;
    ActionSelector(
        action_profile = ecmp_profile,
        hash = ecmp_hash,
        mode = SelectorMode_t.FAIR,
        max_group_size = 128,
        num_groups = 1
    ) ecmp_sel;

    action to_port(PortId_t eg_port) {
        ig_tm_md.ucast_egress_port = eg_port;
        ig_tm_md.bypass_egress = 0x1;
    }

    table ecmp {
        key = {
            use_ecmp: exact;
            hdr.ipv4.src_addr: selector;
            hdr.ipv4.dst_addr: selector;
            hdr.ipv4.protocol: selector;
            meta.l4_lookup.src_port: selector;
            meta.l4_lookup.dst_port: selector;
        }
        actions = {
            to_port;
        }
        size = 4;
        implementation = ecmp_sel;
    }

    table port_map {
        key = {
            ig_intr_md.ingress_port: exact;
        }
        actions = {
            to_port;
        }
        size = 32;
    }

    apply {
        if (hdr.ipv4.isValid()) {
            if (ig_intr_md.ingress_port == CLIENT_PORT) {
                use_ecmp = 1;
                ecmp.apply();
            } else if (ig_intr_md.ingress_port == SERVER_PORT) {
                to_port(CLIENT_PORT);
            } else {
                port_map.apply();
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
    state start {
        pkt.extract(eg_intr_md);
        transition accept;
    }
}

control Egress(inout my_egress_headers_t hdr, inout my_egress_metadata_t meta,
               in egress_intrinsic_metadata_t eg_intr_md, in egress_intrinsic_metadata_from_parser_t eg_prsr_md,
               inout egress_intrinsic_metadata_for_deparser_t eg_dprsr_md, inout egress_intrinsic_metadata_for_output_port_t eg_oport_md) {
    apply {}
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
