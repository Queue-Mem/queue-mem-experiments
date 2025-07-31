#!/bin/bash

source set_env.bash

while getopts p:t:n:r: flag
do
    case "${flag}" in
        p) path=${OPTARG};;
        t) profile=${OPTARG};;
        n) nf=${OPTARG};;
        r) runs=${OPTARG};;
    esac
done

if [ -z "$path" ] || [ -z "$profile" ] || [ -z "$nf" ] || [ -z "$runs" ]; then
        echo 'You missed some parameters' >&2
        exit 1
fi

profile_file="$profile.py"

echo "$(date +'%m-%d-%y-%T') - Starting experiments with the following parameters: " > log.txt

echo "  Output Directory: $path" >> log.txt
echo "  Input Profile: $profile" >> log.txt
echo "  NF: $nf" >> log.txt

echo "$(date +'%m-%d-%y-%T') - Deleting logs from $QUEUEMEM_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $TOF2_PATH/logs/*"
echo "$(date +'%m-%d-%y-%T') - Deleting logs from $MCAST_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sudo rm -rf $MULTICAST_PATH/logs/*"

echo "$(date +'%m-%d-%y-%T') - Cleaning processes..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME -t "sudo killall -9 run_switchd.sh; sudo killall -9 run_bfshell.sh; sudo killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME -t "sudo killall -9 run_switchd.sh; sudo killall -9 run_bfshell.sh; sudo killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
tmux kill-session -t queue-experiments

echo "Setting DEFAULT_N_PAYLOADS=2" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "mv $QUEUEMEM_PATH/setup.py $QUEUEMEM_PATH/setup.py.bak; sed 's/DEFAULT_N_PAYLOADS = .*/DEFAULT_N_PAYLOADS = 2/g' $QUEUEMEM_PATH/setup.py.bak > $QUEUEMEM_PATH/setup.py"
echo "Setting queues_per_slice = 12" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sed -i 's/queues_per_slice = .*/queues_per_slice = 12/g' $QUEUEMEM_PATH/setup.py"

sleep 2
for ((i=1; i<=runs; i++))
do
    echo "$(date +'%m-%d-%y-%T') - trex ~ Start Run ${i}" >> log.txt

    tmux kill-session -t queue-experiments
    tmux new-session -d -s queue-experiments

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME SDE=$MULTICAST_TOFINO_SDE SDE_INSTALL=$MULTICAST_TOFINO_SDE_INSTALL '$MULTICAST_TOFINO_SDE/run_switchd.sh -p bq_ecmp'" Enter

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME SDE=$MULTICAST_TOFINO_SDE SDE_INSTALL=$MULTICAST_TOFINO_SDE_INSTALL '$MULTICAST_TOFINO_SDE/run_bfshell.sh -i -b $MULTICAST_PATH/setup_bq_ecmp.py'" Enter
    
    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME SDE=$QUEUEMEM_TOFINO_SDE SDE_INSTALL=$QUEUEMEM_TOFINO_SDE_INSTALL '$QUEUEMEM_TOFINO_SDE/run_switchd.sh --arch tf2 -p queuemem'" Enter

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME SDE=$QUEUEMEM_TOFINO_SDE SDE_INSTALL=$QUEUEMEM_TOFINO_SDE_INSTALL '$QUEUEMEM_TOFINO_SDE/run_bfshell.sh -i -b $QUEUEMEM_PATH/setup.py'" Enter

    tmux select-pane -t 0
    tmux split-window -h -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$IPERF_CLIENT_NAME_1 -t 'cd $TREX_PATH; sudo ./t-rex-64 -i --astf --cfg $TREX_CONFIG_PATH/config-server.yaml -c 31'" Enter

    tmux select-pane -t 0
    tmux split-window -h -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$IPERF_CLIENT_NAME_1 -t 'echo sleep; sleep 30; mkdir -p $TREX_CONFIG_PATH/results; PYTHONPATH=$TREX_PATH/automation/trex_control_plane/interactive python3.8 $TREX_CONFIG_PATH/start_trex_server.py $TREX_CONFIG_PATH/$profile_file $TREX_CONFIG_PATH/results/$i.json; sleep 5'; tmux kill-session -t queue-experiments" Enter

    tmux select-pane -t 0
    tmux split-window -h -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_1 -t 'echo $NF_SERVER_USER_PASS | sudo -S $NF_PATH --dpdk -l 0-15 -- $nf'" Enter
    
    tmux select-pane -t 0
    tmux send-keys -t queue-experiments "sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_2 -t 'echo $NF_SERVER_USER_PASS | sudo -S $NF_PATH --dpdk -l 0-15 -- $nf'" Enter

    tmux a -t queue-experiments

    echo "$(date +'%m-%d-%y-%T') - Cleaning processes..." >> log.txt
    sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME -t "killall -9 run_switchd.sh; killall -9 run_bfshell.sh; killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
    sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME -t "killall -9 run_switchd.sh; killall -9 run_bfshell.sh; killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
    sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$IPERF_SERVER_NAME_1 -t "sudo killall -9 t-rex-64; sudo killall -9 _t-rex-64"
    sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_1 -t "killall -9 click"
    sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_2 -t "killall -9 click"
    tmux kill-session -t queue-experiments
    
    echo "$(date +'%m-%d-%y-%T') - trex ~ End Run ${i}" >> log.txt

    sleep 5
done

sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $QUEUEMEM_PATH/setup.py; sudo mv $QUEUEMEM_PATH/setup.py.bak $QUEUEMEM_PATH/setup.py"

RESULT_DIR=$path/$profile

mkdir -p $RESULT_DIR

echo "Copying $IPERF_CLIENT_NAME_1 logs in $RESULTS_DIR" >> log.txt
sshpass -p $NF_SERVER_USER_PASS scp -r $NF_SERVER_USERNAME@$IPERF_CLIENT_NAME_1:$TREX_CONFIG_PATH/results/* $RESULT_DIR/

echo "Deleting logs from $QUEUEMEM_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $QUEUEMEM_PATH/logs/*"

echo "Deleting logs from $MCAST_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sudo rm -rf $MULTICAST_PATH/logs/*"

echo "Deleting logs from $IPERF_CLIENT_NAME_1..." >> log.txt
sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$IPERF_CLIENT_NAME_1 "sudo rm -rf $TREX_CONFIG_PATH/results"
