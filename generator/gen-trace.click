d :: DPDKInfo(200000)

define($bout 32)
define($INsrcmac b8:83:03:6f:43:11)
define($RAW_INsrcmac b883036f4311)
define($INdstmac 00:00:00:00:00:00)
define($RAW_INdstmac 000000000000)

define($ignore 0)
define($replay_count 100)
define($quick true)
define($txverbose 99)
define($rxverbose 99)

elementclass MyNull { [0-7] => [0-7]; };

fdIN0 :: FromDump(/mnt/traces/caida-18/caida18-32x.forcedudp.pcap-1, STOP true, TIMING 1, TIMING_FNT "1000", END_AFTER 0, ACTIVE true, BURST 32);
fdIN1 :: FromDump(/mnt/traces/caida-18/caida18-32x.forcedudp.pcap-2, STOP true, TIMING 1, TIMING_FNT "1000", END_AFTER 0, ACTIVE true, BURST 32);
fdIN2 :: FromDump(/mnt/traces/caida-18/caida18-32x.forcedudp.pcap-3, STOP true, TIMING 1, TIMING_FNT "1000", END_AFTER 0, ACTIVE true, BURST 32);
fdIN3 :: FromDump(/mnt/traces/caida-18/caida18-32x.forcedudp.pcap-4, STOP true, TIMING 1, TIMING_FNT "1000", END_AFTER 0, ACTIVE true, BURST 32);
fdIN4 :: FromDump(/mnt/traces/caida-18/caida18-32x.forcedudp.pcap-5, STOP true, TIMING 1, TIMING_FNT "1000", END_AFTER 0, ACTIVE true, BURST 32);
fdIN5 :: FromDump(/mnt/traces/caida-18/caida18-32x.forcedudp.pcap-6, STOP true, TIMING 1, TIMING_FNT "1000", END_AFTER 0, ACTIVE true, BURST 32);
fdIN6 :: FromDump(/mnt/traces/caida-18/caida18-32x.forcedudp.pcap-7, STOP true, TIMING 1, TIMING_FNT "1000", END_AFTER 0, ACTIVE true, BURST 32);
fdIN7 :: FromDump(/mnt/traces/caida-18/caida18-32x.forcedudp.pcap-8, STOP true, TIMING 1, TIMING_FNT "1000", END_AFTER 0, ACTIVE true, BURST 32);

tdIN :: ToDPDKDevice(0, BLOCKING true, BURST $bout, VERBOSE $txverbose, IQUEUE $bout, NDESC 0, TCO 0)

elementclass Numberise { $magic |
    input -> Strip(14) -> check :: MarkIPHeader -> nPacket :: NumberPacket(42) -> StoreData(40, $magic) -> ResetIPChecksum -> Unstrip(14) -> output
}

elementclass Generator { $magic |
    input
    -> MarkMACHeader
    -> EnsureDPDKBuffer
    -> doethRewrite :: { input[0] -> active::Switch(OUTPUT 0)[0] -> rwIN :: EtherRewrite($INsrcmac, $INdstmac) -> [0]output; active[1] -> [0]output }
    -> Pad
    -> Numberise($magic)
    -> avgSIN :: AverageCounter(IGNORE 0)
    -> output;
}

rr :: MyNull;
fdIN0 -> unqueue0 :: Unqueue() -> [0]rr
fdIN1 -> unqueue1 :: Unqueue() -> [1]rr
fdIN2 -> unqueue2 :: Unqueue() -> [2]rr
fdIN3 -> unqueue3 :: Unqueue() -> [3]rr
fdIN4 -> unqueue4 :: Unqueue() -> [4]rr
fdIN5 -> unqueue5 :: Unqueue() -> [5]rr
fdIN6 -> unqueue6 :: Unqueue() -> [6]rr
fdIN7 -> unqueue7 :: Unqueue() -> [7]rr

rr[0] -> gen0 :: Generator(\<5700>) -> tdIN; StaticThreadSched(fdIN0 0/1, unqueue0 0/1)
rr[1] -> gen1 :: Generator(\<5701>) -> tdIN; StaticThreadSched(fdIN1 0/2, unqueue1 0/2)
rr[2] -> gen2 :: Generator(\<5702>) -> tdIN; StaticThreadSched(fdIN2 0/3, unqueue2 0/3)
rr[3] -> gen3 :: Generator(\<5703>) -> tdIN; StaticThreadSched(fdIN3 0/4, unqueue3 0/4)
rr[4] -> gen4 :: Generator(\<5704>) -> tdIN; StaticThreadSched(fdIN4 0/5, unqueue4 0/5)
rr[5] -> gen5 :: Generator(\<5705>) -> tdIN; StaticThreadSched(fdIN5 0/6, unqueue5 0/6)
rr[6] -> gen6 :: Generator(\<5706>) -> tdIN; StaticThreadSched(fdIN6 0/7, unqueue6 0/7)
rr[7] -> gen7 :: Generator(\<5707>) -> tdIN; StaticThreadSched(fdIN7 0/8, unqueue7 0/8)

avgSIN :: HandlerAggregate(ELEMENT gen0/avgSIN, ELEMENT gen1/avgSIN, ELEMENT gen2/avgSIN, ELEMENT gen3/avgSIN, ELEMENT gen4/avgSIN, ELEMENT gen5/avgSIN, ELEMENT gen6/avgSIN,ELEMENT gen7/avgSIN);

elementclass Receiver { $mac, $dir |
    input[0]
    -> c0 :: Classifier(12/0806 20/0002,
                        12/0800,
                        -)[1]
    -> Strip(14)
    -> magic :: Classifier(40/5700,
			               40/5701,
			               40/5702,
			               40/5703,
			               40/5704,
			               40/5705,
			               40/5706,
			               40/5707,
                           -)

    magic[0] -> Unstrip(14) -> avg0 :: AverageCounterMP(IGNORE $ignore) -> Discard;
    magic[1] -> Unstrip(14) -> avg1 :: AverageCounterMP(IGNORE $ignore) -> Discard;
    magic[2] -> Unstrip(14) -> avg2 :: AverageCounterMP(IGNORE $ignore) -> Discard;
    magic[3] -> Unstrip(14) -> avg3 :: AverageCounterMP(IGNORE $ignore) -> Discard;
    magic[4] -> Unstrip(14) -> avg4 :: AverageCounterMP(IGNORE $ignore) -> Discard;
    magic[5] -> Unstrip(14) -> avg5 :: AverageCounterMP(IGNORE $ignore) -> Discard;
    magic[6] -> Unstrip(14) -> avg6 :: AverageCounterMP(IGNORE $ignore) -> Discard;
    magic[7] -> Unstrip(14) -> avg7 :: AverageCounterMP(IGNORE $ignore) -> Discard;
    magic[8] -> Unstrip(14) -> Print("WARNING: Unknown magic / untimestamped packet", -1) -> Discard;
    
    c0[2] -> Print("WARNING: Non-IP packet !") -> Discard;
    c0[0] -> Discard;

    avg :: HandlerAggregate(ELEMENT avg0, ELEMENT avg1, ELEMENT avg2, ELEMENT avg3, ELEMENT avg4, ELEMENT avg5, ELEMENT avg6, ELEMENT avg7);
}

receiveIN :: FromDPDKDevice(0, VERBOSE $rxverbose, MAC $INsrcmac, PROMISC true, PAUSE none, NDESC 0, MAXTHREADS 4, NUMA false)
receiveIN -> RIN :: Receiver($RAW_INsrcmac, "IN");

/*ig :: Script(TYPE ACTIVE,
    set s $(now),
    set lastcount 0,
    set lastbytes 0,
    set lastbytessent 0,
    set lastsent 0,
    set lastdrop 0,
    set last $s,
    set indexB 0,
    set indexC 0,
    set indexD 0,
    label loop,
    wait 1s,
    set n $(now),
    set t $(sub $n $s),
    set elapsed $(sub $n $last),
    set last $n,
    set count $(RIN/avg.add count),
    set sent $(avgSIN.add count),
    set bytessent $(avgSIN.add byte_count),
    set bytes $(RIN/avg.add byte_count),
    print "IG-$t-RESULT-IGCOUNT $(sub $count $lastcount)",
    print "IG-$t-RESULT-IGSENT $(sub $sent $lastsent)",
    print "IG-$t-RESULT-IGBYTESSENT $(sub $bytessent $lastbytessent)",
    set drop $(sub $sent $count),
    print "IG-$t-RESULT-IGDROPPED $(sub $drop $lastdrop)",
    set lastdrop $drop,
    print "IG-$t-RESULT-IGTHROUGHPUT $(div $(mul $(add $(mul $(sub $count $lastcount) 24) $(sub $bytes $lastbytes)) 8) $elapsed)",
    set lastcount $count,
    set lastsent $sent,
    set lastbytes $bytes,
    set lastbytessent $bytessent,
    goto loop
)

StaticThreadSched(ig 15);*/

dm :: DriverManager(
    print "Waiting 2 seconds before launching generation...",
    wait 2s,
    print "EVENT GEN_BEGIN",
    print "Starting gen...",
    print "Starting timer wait...",
    set starttime $(now),
    wait 10,
    set stoptime $(now),
    print "EVENT GEN_DONE",
    wait 1s,
    stop
);

StaticThreadSched(dm 15);

