#!/bin/bash

while getopts d: flag
do
    case "${flag}" in
        d) dir=${OPTARG};;
    esac
done

if [ -z "$dir" ]; then
        echo 'You missed some parameters' >&2
        exit 1
fi

 for i in 2 4 6 8 10 12 14
 do
     bash 1_run_experiment_throughput.sh -p $dir/throughput -m $i
     sleep 5
 done

 bash 2_run_experiment_throughput_incremental.sh -p $dir/incremental -m 14 -t queuemem -d 0
 bash 2_run_experiment_throughput_incremental.sh -p $dir/incremental -m 14 -t simple_forwarder -d 0
 bash 2_run_experiment_throughput_incremental.sh -p $dir/incremental_drops -m 14 -t queuemem -d 3

 bash 3_run_experiment_throughput_random.sh -p $dir/random -m 14 -t queuemem -d 0
 bash 3_run_experiment_throughput_random.sh -p $dir/random -m 14 -t simple_forwarder -d 0
 bash 3_run_experiment_throughput_random.sh -p $dir/random_drops -m 14 -t queuemem -d 3

 bash 4_run_experiment_throughput_peak.sh -p $dir/peak -m 14 -t queuemem -d 0
 bash 4_run_experiment_throughput_peak.sh -p $dir/peak -m 14 -t simple_forwarder -d 0
 bash 4_run_experiment_throughput_peak.sh -p $dir/peak_drops -m 14 -t queuemem -d 3

 bash 5_run_experiment_throughput_trace.sh -p $dir/caida -m 14 -t queuemem -n caida -d 0
 bash 5_run_experiment_throughput_trace.sh -p $dir/caida -m 14 -t simple_forwarder -n caida -d 0
 bash 5_run_experiment_throughput_trace.sh -p $dir/caida_drops -m 14 -t queuemem -n caida -d 3

 bash 5_run_experiment_throughput_trace.sh -p $dir/mawi -m 14 -t queuemem -n mawi -d 0
 bash 5_run_experiment_throughput_trace.sh -p $dir/mawi -m 14 -t simple_forwarder -n mawi -d 0
 bash 5_run_experiment_throughput_trace.sh -p $dir/mawi_drops -m 14 -t queuemem -n mawi -d 3

 for i in 2 4 6 8 10 12
 do
     bash 6_run_experiment_throughput_nf.sh -p $dir/throughput_nf/fc_lb_rl -m $i -g 79 -n /home/hamid/workspace/queuejammer/chain-fc-lb-rl.click
     sleep 2
 done

 for i in 2 4 6 8 10 12
 do
     bash 6_run_experiment_throughput_nf.sh -p $dir/throughput_nf/lb_aes -m $i -g 79 -n /home/hamid/workspace/queuejammer/chain-lb-aes.click
     sleep 2
 done

 for i in 0 2 3 5 10
 do
     bash 9_run_experiment_drops.sh -p $dir/drops -m 14 -d $i -t 0
     sleep 2
 done

 for i in 0 1 2 3 5 10
 do
     bash 9_run_experiment_drops.sh -p $dir/tail_drops -m 14 -d $i -t 1
     sleep 2
 done

 bash 10_run_experiment_throughput_iperf.sh -p $dir/bg_traffic_iperf_tp -m 14 -n caida
 bash 11_run_experiment_lat_bg.sh -p $dir/bg_traffic_lat -m 14 -n dual -f /home/hamid/workspace/queuejammer/chain-lb.click

 for i in 1 2 4 8 16 20
 do
     bash 12_run_experiment_reordering.sh -p $dir/reordering -m 14 -s $i -c 125
     sleep 2
 done

 bash 13_run_experiment_iperf_full.sh -p $dir/iperf_all

 bash 14_run_experiment_trex.sh -p $dir/trex -t allreduce -n /home/hamid/workspace/queuejammer/chain-fc.click
bash 14_run_experiment_trex.sh -p $dir/trex -t http_post -n /home/hamid/workspace/queuejammer/chain-fc.click

