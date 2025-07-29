#!/bin/bash

source set_env.bash

while getopts p:m:n:l: flag
do
    case "${flag}" in
        p) path=${OPTARG};;
    esac
done

if [ -z "$path" ]; then
        echo 'You missed some parameters' >&2
        exit 1
fi

echo "$(date +'%m-%d-%y-%T') - Starting experiments with the following parameters: " > log.txt

echo "  Output Directory: $path" >> log.txt

echo "$(date +'%m-%d-%y-%T') - Deleting logs from $QUEUEMEM_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $QUEUEMEM_PATH/logs/*"

echo "$(date +'%m-%d-%y-%T') - Cleaning processes..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME -t "sudo killall -9 run_switchd.sh; sudo killall -9 run_bfshell.sh; sudo killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
tmux kill-session -t queue-experiments

echo "Setting DEFAULT_N_PAYLOADS=1" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "mv $QUEUEMEM_PATH/setup.py $QUEUEMEM_PATH/setup.py.bak; sed 's/DEFAULT_N_PAYLOADS = .*/DEFAULT_N_PAYLOADS = 1/g' $QUEUEMEM_PATH/setup.py.bak > $QUEUEMEM_PATH/setup.py"
echo "Setting queues_per_slice = 30" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sed -i 's/queues_per_slice = .*/queues_per_slice = 30/g' $QUEUEMEM_PATH/setup.py"
echo "Setting TCP_EXPERIMENT=True" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sed -i 's/TCP_EXPERIMENT = .*/TCP_EXPERIMENT = True/g' $QUEUEMEM_PATH/setup.py"

sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_1 -t "mkdir -p $GENERATOR_PATH/iperf-logs"

sleep 2
for i in 1 2 3 4 5 6 7 8 9 10
do
    echo "$(date +'%m-%d-%y-%T') - iperf full ~ Start Run ${i}" >> log.txt

    tmux kill-session -t queue-experiments
    tmux new-session -d -s queue-experiments

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME SDE=$QUEUEMEM_TOFINO_SDE SDE_INSTALL=$QUEUEMEM_TOFINO_SDE_INSTALL '$QUEUEMEM_TOFINO_SDE/run_switchd.sh --arch tf2 -p queuemem'" Enter

    tmux split-window -h -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME SDE=$QUEUEMEM_TOFINO_SDE SDE_INSTALL=$QUEUEMEM_TOFINO_SDE_INSTALL '$QUEUEMEM_TOFINO_SDE/run_bfshell.sh -i -b $QUEUEMEM_PATH/setup.py'" Enter

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_1 -t 'echo $NF_SERVER_USER_PASS | sudo -S $NF_PATH --dpdk -l 0-15 -- /home/hamid/workspace/queuejammer/chain-lb.click'" Enter
    
    tmux split-window -h -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_2 -t 'echo $NF_SERVER_USER_PASS | sudo -S $NF_PATH --dpdk -l 0-15 -- /home/hamid/workspace/queuejammer/chain-lb.click'" Enter
    
    # iperf Servers
    tmux select-pane -t 0
    tmux split-window -h -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$IPERF_SERVER_NAME_1 -t 'echo sleep; sleep 30; sudo modprobe tcp_bbr; sudo ip neigh del 192.168.203.32 dev cx5_0if1; sudo sysctl -w net.core.rmem_max=536870912; sudo sysctl -w net.core.wmem_max=536870912; sudo sysctl -w net.ipv4.tcp_rmem=\"4096 87380 536870912\"; sudo sysctl -w net.ipv4.tcp_wmem=\"4096 65536 536870912\"; sudo sysctl -w net.ipv4.tcp_window_scaling=1; sudo sysctl -w net.ipv4.tcp_sack=1; sudo ip link set cx5_0if1 promisc on; sudo ip neigh add 192.168.203.32 lladdr b8:ce:f6:b0:2e:63 dev cx5_0if1; sudo cpupower --cpu 0-15 frequency-set -d 3600M -u 3600M 2> /dev/null 1> /dev/null; sudo ethtool -G cx5_0if1 rx 1024 tx 8192 2> /dev/null 1> /dev/null; sudo ethtool -K cx5_0if1 lro on gro on tso on 2> /dev/null 1> /dev/null; sudo ifconfig cx5_0if1 mtu 4000 2> /dev/null 1> /dev/null; sudo ethtool -A cx5_0if1 rx off tx off 2>/dev/null 1> /dev/null; sudo ethtool -L cx5_0if1 combined 16; sudo service irqbalance stop; numactl --cpunodebind=0 iperf3 -s -p 5201'" Enter

    # iperf Clients
    tmux select-pane -t 0
    tmux send-keys -t queue-experiments "sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$IPERF_CLIENT_NAME_1 -t 'mkdir -p $GENERATOR_PATH/iperf-logs/$i; echo sleep; sleep 31; killall iperf3; sudo modprobe tcp_bbr; sudo ip neigh del 192.168.203.12 dev cx6_200if1; sudo ip link set cx6_200if1 promisc on; sudo sysctl -w net.core.rmem_max=536870912; sudo sysctl -w net.core.wmem_max=536870912; sudo sysctl -w net.ipv4.tcp_rmem=\"4096 87380 536870912\"; sudo sysctl -w net.ipv4.tcp_wmem=\"4096 65536 536870912\"; sudo sysctl -w net.ipv4.tcp_window_scaling=1; sudo sysctl -w net.ipv4.tcp_sack=1; sudo ip neigh add 192.168.203.12 lladdr 98:03:9b:03:55:a1 dev cx6_200if1; sudo cpupower --cpu 0-63 frequency-set -d 3700M -u 3700M 2> /dev/null 1> /dev/null; sudo ethtool -G cx6_200if1 rx 8192 tx 8192 2> /dev/null 1> /dev/null; sudo ethtool -K cx6_200if1 lro on gro on tso on 2> /dev/null 1> /dev/null; sudo ifconfig cx6_200if1 mtu 4000 2> /dev/null 1> /dev/null; sudo ethtool -A cx6_200if1 rx off tx off 2>/dev/null 1> /dev/null; sudo ethtool -L cx6_200if1 combined 32; sudo service irqbalance stop; sudo su -c 'ulimit -n 1048576'; sudo ulimit -n 1048576; numactl --cpunodebind=0 iperf3 -c 192.168.203.12 -t 10 -P 128 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf.json -p 5201 -C bbr -Z --repeating-payload -l 1M; sleep 5'; tmux kill-session -t queue-experiments" Enter

    tmux a -t queue-experiments

    echo "$(date +'%m-%d-%y-%T') - Cleaning processes..." >> log.txt
    sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME -t "killall -9 run_switchd.sh; killall -9 run_bfshell.sh; killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
    sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$IPERF_SERVER_NAME_1 -t "killall -9 iperf3"
    sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$IPERF_CLIENT_NAME_1 -t "killall -9 iperf3"
    sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_1 -t "killall -9 click"
    sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_2 -t "killall -9 click"

    tmux kill-session -t queue-experiments
    
    echo "$(date +'%m-%d-%y-%T') - iperf full ~ End Run ${i}" >> log.txt

    sleep 5
done

sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $QUEUEMEM_PATH/setup.py; sudo mv $QUEUEMEM_PATH/setup.py.bak $QUEUEMEM_PATH/setup.py"

RESULT_DIR=$path

mkdir -p $RESULT_DIR/tofino2-logs

echo "Copying $QUEUEMEM_TOFINO_NAME logs in $RESULT_DIR" >> log.txt
sshpass -p $TOFINO_USER_PASS scp -r $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME:$QUEUEMEM_PATH/logs/* $RESULT_DIR/tofino2-logs

echo "Copying $IPERF_CLIENT_NAME_1 logs in $RESULTS_DIR" >> log.txt
sshpass -p $NF_SERVER_USER_PASS scp -r $NF_SERVER_USERNAME@$IPERF_CLIENT_NAME_1:$GENERATOR_PATH/iperf-logs/ $RESULT_DIR/iperf-logs/

echo "Deleting logs from $QUEUEMEM_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $QUEUEMEM_PATH/logs/*"

echo "Deleting logs from $IPERF_CLIENT_NAME_1..." >> log.txt
sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$IPERF_CLIENT_NAME_1 "sudo rm -rf $GENERATOR_PATH/iperf-logs"
