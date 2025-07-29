d :: DPDKInfo(200000)

define($bout 32)
define($INsrcmac b8:83:03:6f:43:11)
define($RAW_INsrcmac b883036f4311)

define($INdstmac d5:83:03:6f:32:14)
define($RAW_INdstmac b883036f3214)

define($ignore 0)
define($replay_count 100)
define($quick true)
define($txverbose 99)
define($rxverbose 99)

elementclass MyNull { [0-9]=>[0- 9 ]; };

fdIN0 :: FromDump(/mnt/traces/mawi-25/splitsv4/mawi-ipv4.pcap-1, TIMING 0, BURST 32, STOP true);
fdIN1 :: FromDump(/mnt/traces/mawi-25/splitsv4/mawi-ipv4.pcap-2, TIMING 0, BURST 32, STOP true);
fdIN2 :: FromDump(/mnt/traces/mawi-25/splitsv4/mawi-ipv4.pcap-3, TIMING 0, BURST 32, STOP true);
fdIN3 :: FromDump(/mnt/traces/mawi-25/splitsv4/mawi-ipv4.pcap-4, TIMING 0, BURST 32, STOP true);
fdIN4 :: FromDump(/mnt/traces/mawi-25/splitsv4/mawi-ipv4.pcap-5, TIMING 0, BURST 32, STOP true);
fdIN5 :: FromDump(/mnt/traces/mawi-25/splitsv4/mawi-ipv4.pcap-6, TIMING 0, BURST 32, STOP true);
fdIN6 :: FromDump(/mnt/traces/mawi-25/splitsv4/mawi-ipv4.pcap-7, TIMING 0, BURST 32, STOP true);
fdIN7 :: FromDump(/mnt/traces/mawi-25/splitsv4/mawi-ipv4.pcap-8, TIMING 0, BURST 32, STOP true);
fdIN8 :: FromDump(/mnt/traces/mawi-25/splitsv4/mawi-ipv4.pcap-9, TIMING 0, BURST 32, STOP true);
fdIN9 :: FromDump(/mnt/traces/mawi-25/splitsv4/mawi-ipv4.pcap-10, TIMING 0, BURST 32, STOP true);


tdIN ::

    ToDPDKDevice(0, BLOCKING true, BURST $bout, VERBOSE $txverbose, IQUEUE $bout, NDESC 1024, IPCO true )

elementclass NoTimestampDiff { $a, $b, $c, $d |
input -> output;
Idle->[1]output;
}

elementclass Numberise { $magic |
    input-> Strip(14)
     -> check :: MarkIPHeader
    -> ResetIPChecksum() -> Unstrip(14) -> output
}

ender :: Script(TYPE PASSIVE,
                print "Limit of 40000000 reached",
                stop,
                stop);
 rr :: MyNull; 

fdIN0 -> limit0   :: Counter(COUNT_CALL 50000000 ender.run)-> unqueue0 ::  RatedUnqueue(1200000, BURST 32)  -> [0]rr
fdIN1 -> limit1   :: Counter(COUNT_CALL 50000000 ender.run)-> unqueue1 ::  RatedUnqueue(1200000, BURST 32)  -> [1]rr
fdIN2 -> limit2   :: Counter(COUNT_CALL 50000000 ender.run)-> unqueue2 ::  RatedUnqueue(1200000, BURST 32)  -> [2]rr
fdIN3 -> limit3   :: Counter(COUNT_CALL 50000000 ender.run)-> unqueue3 ::  RatedUnqueue(1200000, BURST 32)  -> [3]rr
fdIN4 -> limit4   :: Counter(COUNT_CALL 50000000 ender.run)-> unqueue4 ::  RatedUnqueue(1200000, BURST 32)  -> [4]rr
fdIN5 -> limit5   :: Counter(COUNT_CALL 50000000 ender.run)-> unqueue5 ::  RatedUnqueue(1200000, BURST 32)  -> [5]rr
fdIN6 -> limit6   :: Counter(COUNT_CALL 50000000 ender.run)-> unqueue6 ::  RatedUnqueue(1200000, BURST 32)  -> [6]rr
fdIN7 -> limit7   :: Counter(COUNT_CALL 50000000 ender.run)-> unqueue7 ::  RatedUnqueue(1200000, BURST 32)  -> [7]rr
fdIN8 -> limit8   :: Counter(COUNT_CALL 50000000 ender.run)-> unqueue8 ::  RatedUnqueue(1200000, BURST 32)  -> [8]rr
fdIN9 -> limit9   :: Counter(COUNT_CALL 50000000 ender.run)-> unqueue9 ::  RatedUnqueue(1200000, BURST 32)  -> [9]rr


elementclass Generator { $magic |
input
 
  -> MarkMACHeader
-> EnsureDPDKBuffer
// -> EtherEncap(0x0800, $INsrcmac, $INdstmac)
-> EtherRewrite($INsrcmac, $INdstmac)
-> Pad(MAXLENGTH 1500)
  -> Numberise($magic)
  -> avgSIN :: AverageCounter(IGNORE $ignore)
//  -> Print(MAXLENGTH 2000)
  -> output;
}

rr[0] -> gen0 :: Generator(\<5700>) -> tdIN;StaticThreadSched(fdIN0 0/1 , unqueue0 0/1)
rr[1] -> gen1 :: Generator(\<5701>) -> tdIN;StaticThreadSched(fdIN1 0/2 , unqueue1 0/2)
rr[2] -> gen2 :: Generator(\<5702>) -> tdIN;StaticThreadSched(fdIN2 0/3 , unqueue2 0/3)
rr[3] -> gen3 :: Generator(\<5703>) -> tdIN;StaticThreadSched(fdIN3 0/4 , unqueue3 0/4)
rr[4] -> gen4 :: Generator(\<5704>) -> tdIN;StaticThreadSched(fdIN4 0/5 , unqueue4 0/5)
rr[5] -> gen5 :: Generator(\<5705>) -> tdIN;StaticThreadSched(fdIN5 0/6 , unqueue5 0/6)
rr[6] -> gen6 :: Generator(\<5706>) -> tdIN;StaticThreadSched(fdIN6 0/7 , unqueue6 0/7)
rr[7] -> gen7 :: Generator(\<5707>) -> tdIN;StaticThreadSched(fdIN7 0/8 , unqueue7 0/8)
rr[8] -> gen8 :: Generator(\<5708>) -> tdIN;StaticThreadSched(fdIN8 0/9 , unqueue8 0/9)
rr[9] -> gen9 :: Generator(\<5709>) -> tdIN;StaticThreadSched(fdIN9 0/10 , unqueue9 0/10)






receiveIN :: FromDPDKDevice(0, VERBOSE $rxverbose, MAC $INsrcmac, PROMISC true, PAUSE full, NDESC 1024, MAXTHREADS 2, MINQUEUES 2, NUMA false, RSS_AGGREGATE true, ACTIVE 1)

elementclass Receiver { $mac, $dir |
    input[0]
 -> c :: Classifier(-, 0/ffffffffffff)
    -> Strip(14)
    -> CheckIPHeader(CHECKSUM false)

-> magic :: {[0]-> RoundRobinSwitch(SPLITBATCH false)[0-9] => [0-9]output;Idle->[10]output;}

    c[1] //Not for this computer or broadcasts
    -> Discard;

magic[0] -> tsd0 :: NoTimestampDiff(gen0/rt, OFFSET 42, N 80002048, SAMPLE 10 ) -> Unstrip(14) ->  avg0 :: AverageCounterMP(IGNORE $ignore) -> Discard;  tsd0[1] -> Print('WARNING: Untimestamped packet on thread 0', 64) -> Discard;
magic[1] -> tsd1 :: NoTimestampDiff(gen1/rt, OFFSET 42, N 80002048, SAMPLE 10 ) -> Unstrip(14) ->  avg1 :: AverageCounterMP(IGNORE $ignore) -> Discard;  tsd1[1] -> Print('WARNING: Untimestamped packet on thread 1', 64) -> Discard;
magic[2] -> tsd2 :: NoTimestampDiff(gen2/rt, OFFSET 42, N 80002048, SAMPLE 10 ) -> Unstrip(14) ->  avg2 :: AverageCounterMP(IGNORE $ignore) -> Discard;  tsd2[1] -> Print('WARNING: Untimestamped packet on thread 2', 64) -> Discard;
magic[3] -> tsd3 :: NoTimestampDiff(gen3/rt, OFFSET 42, N 80002048, SAMPLE 10 ) -> Unstrip(14) ->  avg3 :: AverageCounterMP(IGNORE $ignore) -> Discard;  tsd3[1] -> Print('WARNING: Untimestamped packet on thread 3', 64) -> Discard;
magic[4] -> tsd4 :: NoTimestampDiff(gen4/rt, OFFSET 42, N 80002048, SAMPLE 10 ) -> Unstrip(14) ->  avg4 :: AverageCounterMP(IGNORE $ignore) -> Discard;  tsd4[1] -> Print('WARNING: Untimestamped packet on thread 4', 64) -> Discard;
magic[5] -> tsd5 :: NoTimestampDiff(gen5/rt, OFFSET 42, N 80002048, SAMPLE 10 ) -> Unstrip(14) ->  avg5 :: AverageCounterMP(IGNORE $ignore) -> Discard;  tsd5[1] -> Print('WARNING: Untimestamped packet on thread 5', 64) -> Discard;
magic[6] -> tsd6 :: NoTimestampDiff(gen6/rt, OFFSET 42, N 80002048, SAMPLE 10 ) -> Unstrip(14) ->  avg6 :: AverageCounterMP(IGNORE $ignore) -> Discard;  tsd6[1] -> Print('WARNING: Untimestamped packet on thread 6', 64) -> Discard;
magic[7] -> tsd7 :: NoTimestampDiff(gen7/rt, OFFSET 42, N 80002048, SAMPLE 10 ) -> Unstrip(14) ->  avg7 :: AverageCounterMP(IGNORE $ignore) -> Discard;  tsd7[1] -> Print('WARNING: Untimestamped packet on thread 7', 64) -> Discard;
magic[8] -> tsd8 :: NoTimestampDiff(gen8/rt, OFFSET 42, N 80002048, SAMPLE 10 ) -> Unstrip(14) ->  avg8 :: AverageCounterMP(IGNORE $ignore) -> Discard;  tsd8[1] -> Print('WARNING: Untimestamped packet on thread 8', 64) -> Discard;
magic[9] -> tsd9 :: NoTimestampDiff(gen9/rt, OFFSET 42, N 80002048, SAMPLE 10 ) -> Unstrip(14) ->  avg9 :: AverageCounterMP(IGNORE $ignore) -> Discard;  tsd9[1] -> Print('WARNING: Untimestamped packet on thread 9', 64) -> Discard;


avg :: HandlerAggregate( ELEMENT avg0,ELEMENT avg1,ELEMENT avg2,ELEMENT avg3,ELEMENT avg4,ELEMENT avg5,ELEMENT avg6,ELEMENT avg7,ELEMENT avg8,ELEMENT avg9 );

    magic[10]
    -> Unstrip(14)
    -> Print("WARNING: Unknown magic / untimestamped packet", -1)
    -> Discard;


}

receiveIN
-> Classifier(12/0800) -> MarkIPHeader(14) -> RIN :: Receiver($RAW_INsrcmac,"IN");



avgSIN :: HandlerAggregate( ELEMENT gen0/avgSIN,ELEMENT gen1/avgSIN,ELEMENT gen2/avgSIN,ELEMENT gen3/avgSIN,ELEMENT gen4/avgSIN,ELEMENT gen5/avgSIN,ELEMENT gen6/avgSIN,ELEMENT gen7/avgSIN,ELEMENT gen8/avgSIN,ELEMENT gen9/avgSIN );

dm :: DriverManager(  print "Waiting 2 seconds before launching generation...",
                print "EVENT GEN_STARTING",
                wait 2s,

                print "EVENT GEN_BEGIN",
                print "Starting gen...",
//                write fdIN.active true,
                print "Starting timer wait...",
                set starttime $(now),
                wait 5,
//                write fdIN.active 0,
                set stoptime $(now),
//                wait 8s,
                print "EVENT GEN_DONE",
                print "RESULT-TX $(avgSIN.add link_rate)",
                print "RESULT-TXPPS $(avgSIN.add rate)",
                wait 1s,
                stop);

StaticThreadSched(dm 15);

