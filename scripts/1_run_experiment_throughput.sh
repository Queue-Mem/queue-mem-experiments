#!/bin/bash

source set_env.bash

while getopts p:m:r: flag
do
    case "${flag}" in
        p) path=${OPTARG};;
        m) mcast=${OPTARG};;
        r) runs=${OPTARG};;
    esac
done

if [ -z "$path" ] || [ -z "$mcast" ] || [ -r "$runs" ]; then
        echo 'You missed some parameters' >&2
        exit 1
fi

echo "$(date +'%m-%d-%y-%T') - Starting experiments with the following parameters: " > log.txt

echo "  Output Directory: $path" >> log.txt
echo "  Number Of Multicast: $mcast" >> log.txt
echo "  Number Of Runs: $runs" >> log.txt

echo "$(date +'%m-%d-%y-%T') - Deleting logs from $QUEUEMEM_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $QUEUEMEM_PATH/logs/*"
echo "$(date +'%m-%d-%y-%T') - Deleting logs from $MCAST_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sudo rm -rf $MULTICAST_PATH/logs/*"

echo "$(date +'%m-%d-%y-%T') - Cleaning processes..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME -t "sudo killall -9 run_switchd.sh; sudo killall -9 run_bfshell.sh; sudo killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME -t "sudo killall -9 run_switchd.sh; sudo killall -9 run_bfshell.sh; sudo killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
tmux kill-session -t queue-experiments

echo "Setting MULTICAST=$mcast" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "mv $MULTICAST_PATH/setup_bq_forwarder.py $MULTICAST_PATH/setup_bq_forwarder.py.bak; sed 's/N_MULTICAST = .*/N_MULTICAST = $mcast/g' $MULTICAST_PATH/setup_bq_forwarder.py.bak > $MULTICAST_PATH/setup_bq_forwarder.py"
echo "Setting MAX_RATE=True" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sed -i 's/MAX_RATE = False/MAX_RATE = True/g' $MULTICAST_PATH/setup_bq_forwarder.py"

echo "Setting DEFAULT_N_PAYLOADS=30" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sed -i 's/DEFAULT_N_PAYLOADS = .*/DEFAULT_N_PAYLOADS = 30/g' $QUEUEMEM_PATH/setup.py"
echo "Setting queues_per_slice = 8" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sed -i 's/queues_per_slice = .*/queues_per_slice = 8/g' $QUEUEMEM_PATH/setup.py"

sleep 2
for ((i=1; i<=runs; i++))
do
    echo "$(date +'%m-%d-%y-%T') - Throughput ${mcast}x100Gbps ~ Start Run ${i}" >> log.txt

    tmux kill-session -t queue-experiments
    tmux new-session -d -s queue-experiments

    tmux select-pane -t 0
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME SDE=$MULTICAST_TOFINO_SDE SDE_INSTALL=$MULTICAST_TOFINO_SDE_INSTALL '$MULTICAST_TOFINO_SDE/run_switchd.sh -p bq_forwarder'" Enter

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME SDE=$MULTICAST_TOFINO_SDE SDE_INSTALL=$MULTICAST_TOFINO_SDE_INSTALL '$MULTICAST_TOFINO_SDE/run_bfshell.sh -i -b $MULTICAST_PATH/setup_bq_forwarder.py'; tmux kill-session -t queue-experiments" Enter
    
    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME SDE=$QUEUEMEM_TOFINO_SDE SDE_INSTALL=$QUEUEMEM_TOFINO_SDE_INSTALL '$QUEUEMEM_TOFINO_SDE/run_switchd.sh --arch tf2 -p queuemem'" Enter

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME SDE=$QUEUEMEM_TOFINO_SDE SDE_INSTALL=$QUEUEMEM_TOFINO_SDE_INSTALL '$QUEUEMEM_TOFINO_SDE/run_bfshell.sh -i -b $QUEUEMEM_PATH/setup.py'" Enter

    tmux a -t queue-experiments

    echo "$(date +'%m-%d-%y-%T') - Cleaning processes..." >> log.txt
    sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME -t "killall -9 run_switchd.sh; killall -9 run_bfshell.sh; killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
    sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME -t "killall -9 run_switchd.sh; killall -9 run_bfshell.sh; killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
    tmux kill-session -t queue-experiments
    
    echo "$(date +'%m-%d-%y-%T') - Throughput ${mcast}x100Gbps ~ End Run ${i}" >> log.txt

    sleep 5
done

sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sudo rm -rf $MULTICAST_PATH/setup_bq_forwarder.py; sudo mv $MULTICAST_PATH/setup_bq_forwarder.py.bak $MULTICAST_PATH/setup_bq_forwarder.py"

RESULT_DIR=$path/$mcast

mkdir -p $RESULT_DIR/tofino2-logs
mkdir -p $RESULT_DIR/tofino32p-logs

echo "Copying $QUEUEMEM_TOFINO_NAME logs in $RESULT_DIR" >> log.txt
sshpass -p $TOFINO_USER_PASS scp -r $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME:$QUEUEMEM_PATH/logs/* $RESULT_DIR/tofino2-logs

echo "Copying $MCAST_TOFINO_NAME logs in $RESULT_DIR" >> log.txt
sshpass -p $TOFINO_USER_PASS scp -r $TOFINO_USERNAME@$MCAST_TOFINO_NAME:$MULTICAST_PATH/logs/* $RESULT_DIR/tofino32p-logs

echo "Deleting logs from $QUEUEMEM_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $QUEUEMEM_PATH/logs/*"

echo "Deleting logs from $MCAST_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sudo rm -rf $MULTICAST_PATH/logs/*"