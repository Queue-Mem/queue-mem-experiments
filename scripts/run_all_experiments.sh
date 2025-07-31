#!/bin/bash

while getopts d:r: flag
do
    case "${flag}" in
        d) dir=${OPTARG};;
        r) runs=${OPTARG};;
    esac
done

if [ -z "$dir" ] || [ -z "$runs" ]; then
        echo 'You missed some parameters' >&2
        exit 1
fi

for i in 2 4 6 8 10 12 14
do
    bash 1_run_experiment_throughput.sh -p $dir/throughput -m $i -r $runs
    sleep 5
done

bash 2_run_experiment_throughput_incremental.sh -p $dir/incremental -m 10 -t queuemem -d 0 -r $runs
bash 2_run_experiment_throughput_incremental.sh -p $dir/incremental -m 10 -t simple_forwarder -d 0 -r $runs
bash 2_run_experiment_throughput_incremental.sh -p $dir/incremental_drops -m 10 -t queuemem -d 3 -r $runs

bash 3_run_experiment_throughput_random.sh -p $dir/random -m 10 -t queuemem -d 0 -r $runs
bash 3_run_experiment_throughput_random.sh -p $dir/random -m 10 -t simple_forwarder -d 0 -r $runs
bash 3_run_experiment_throughput_random.sh -p $dir/random_drops -m 10 -t queuemem -d 3 -r $runs

bash 4_run_experiment_throughput_peak.sh -p $dir/peak -m 10 -t queuemem -d 0 -r $runs
bash 4_run_experiment_throughput_peak.sh -p $dir/peak -m 10 -t simple_forwarder -d 0 -r $runs
bash 4_run_experiment_throughput_peak.sh -p $dir/peak_drops -m 10 -t queuemem -d 3 -r $runs

bash 5_run_experiment_throughput_trace.sh -p $dir/caida -m 10 -t queuemem -n caida -d 0 -r $runs
bash 5_run_experiment_throughput_trace.sh -p $dir/caida -m 10 -t simple_forwarder -n caida -d 0 -r $runs
bash 5_run_experiment_throughput_trace.sh -p $dir/caida_drops -m 10 -t queuemem -n caida -d 3 -r $runs

bash 5_run_experiment_throughput_trace.sh -p $dir/mawi -m 10 -t queuemem -n mawi -d 0 -r $runs
bash 5_run_experiment_throughput_trace.sh -p $dir/mawi -m 10 -t simple_forwarder -n mawi -d 0 -r $runs
bash 5_run_experiment_throughput_trace.sh -p $dir/mawi_drops -m 10 -t queuemem -n mawi -d 3 -r $runs

for i in 2 4 6 8 10 12
do
    bash 6_run_experiment_throughput_nf.sh -p $dir/throughput_nf/fc_lb_rl -m $i -g 79 -n /home/hamid/workspace/queuejammer/chain-fc-lb-rl.click -r $runs
    sleep 2
done

for i in 2 4 6 8 10 12
do
    bash 6_run_experiment_throughput_nf.sh -p $dir/throughput_nf/lb_aes -m $i -g 79 -n /home/hamid/workspace/queuejammer/chain-lb-aes.click -r $runs
    sleep 2
done

for i in 0 2 3 5 10
do
    bash 9_run_experiment_drops.sh -p $dir/drops -m 10 -d $i -t 0 -r $runs
    sleep 2
done

for i in 0 1 2 3 5 10
do
    bash 9_run_experiment_drops.sh -p $dir/tail_drops -m 10 -d $i -t 1 -r $runs
    sleep 2
done

bash 10_run_experiment_throughput_iperf.sh -p $dir/bg_traffic_iperf_tp -m 10 -n caida -r $runs
bash 11_run_experiment_lat_bg.sh -p $dir/bg_traffic_lat -m 10 -n dual -f /home/hamid/workspace/queuejammer/chain-lb.click -r $runs

for i in 1 2 4 8 16 20
do
   bash 12_run_experiment_reordering.sh -p $dir/reordering -m 10 -s $i -c 125 -r $runs
   sleep 2
done

bash 13_run_experiment_iperf_full.sh -p $dir/iperf_all -r $runs

bash 14_run_experiment_trex.sh -p $dir/trex -t allreduce -n /home/hamid/workspace/queuejammer/chain-fc.click -r $runs
bash 14_run_experiment_trex.sh -p $dir/trex -t http_post -n /home/hamid/workspace/queuejammer/chain-fc.click -r $runs

