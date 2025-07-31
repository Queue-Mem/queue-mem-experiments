#!/bin/bash

source set_env.bash

while getopts p:m:s:c:r: flag
do
    case "${flag}" in
        p) path=${OPTARG};;
        m) mcast=${OPTARG};;
        s) slf=${OPTARG};;
        c) cons_flows=${OPTARG};;
        r) runs=${OPTARG};;
    esac
done

if [ -z "$path" ] || [ -z "$mcast" ] || [ -z "$slf" ] || [ -z "$cons_flows" ] || [ -r "$runs" ]; then
        echo 'You missed some parameters' >&2
        exit 1
fi

echo "$(date +'%m-%d-%y-%T') - Starting experiments with the following parameters: " > log.txt

echo "  Output Directory: $path" >> log.txt
echo "  Number Of Mulicast: $mcast" >> log.txt
echo "  SLF: $slf" >> log.txt
echo "  Consecutive Flows: $cons_flows" >> log.txt

echo "$(date +'%m-%d-%y-%T') - Deleting logs from $QUEUEMEM_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $TOF2_PATH/logs/*"
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
echo "Setting REORDERING_MEASUREMENT=1" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sed -i 's/REORDERING_MEASUREMENT = .*/REORDERING_MEASUREMENT = 1/g' $MULTICAST_PATH/setup_bq_forwarder.py"
echo "Setting SLF=$slf" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sed -i 's/SLF = .*/SLF = $slf/g' $MULTICAST_PATH/setup_bq_forwarder.py"
echo "Setting CONSECUTIVE_FLOWS=$cons_flows" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sed -i 's/CONSECUTIVE_FLOWS = .*/CONSECUTIVE_FLOWS = $cons_flows/g' $MULTICAST_PATH/setup_bq_forwarder.py"

echo "Setting PKT_GEN_RATE=62" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "mv $MULTICAST_PATH/pktgen_start_1500.py $MULTICAST_PATH/pktgen_start_1500.py.bak; sed 's/PKTGEN_RATE = .*/PKTGEN_RATE = 62/g' $MULTICAST_PATH/pktgen_start_1500.py.bak > $MULTICAST_PATH/pktgen_start_1500.py"

echo "Setting DEFAULT_N_PAYLOADS=80" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "mv $QUEUEMEM_PATH/setup.py $QUEUEMEM_PATH/setup.py.bak; sed 's/DEFAULT_N_PAYLOADS = .*/DEFAULT_N_PAYLOADS = 80/g' $QUEUEMEM_PATH/setup.py.bak > $QUEUEMEM_PATH/setup.py"
echo "Setting queues_per_slice = 2" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sed -i 's/queues_per_slice = .*/queues_per_slice = 2/g' $QUEUEMEM_PATH/setup.py"

sleep 2
for ((i=1; i<=runs; i++))
do
    echo "$(date +'%m-%d-%y-%T') - Reordering ${mcast}x100Gbps ~ Start Run ${i}" >> log.txt

    tmux kill-session -t queue-experiments
    tmux new-session -d -s queue-experiments

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME SDE=$MULTICAST_TOFINO_SDE SDE_INSTALL=$MULTICAST_TOFINO_SDE_INSTALL '$MULTICAST_TOFINO_SDE/run_switchd.sh -p bq_forwarder'" Enter

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME SDE=$MULTICAST_TOFINO_SDE SDE_INSTALL=$MULTICAST_TOFINO_SDE_INSTALL '$MULTICAST_TOFINO_SDE/run_bfshell.sh -i -b $MULTICAST_PATH/setup_bq_forwarder.py'" Enter
    
    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME SDE=$QUEUEMEM_TOFINO_SDE SDE_INSTALL=$QUEUEMEM_TOFINO_SDE_INSTALL '$QUEUEMEM_TOFINO_SDE/run_switchd.sh --arch tf2 -p queuemem'" Enter

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME SDE=$QUEUEMEM_TOFINO_SDE SDE_INSTALL=$QUEUEMEM_TOFINO_SDE_INSTALL '$QUEUEMEM_TOFINO_SDE/run_bfshell.sh -i -b $QUEUEMEM_PATH/setup.py'" Enter
    
    tmux select-pane -t 0
    tmux send-keys -t queue-experiments "sshpass -p $GENERATOR_SERVER_USER_PASS ssh $GENERATOR_SERVER_USERNAME@$GENERATOR_SERVER_NAME -t 'echo sleep; sleep 45; cd $GENERATOR_PATH && echo $GENERATOR_SERVER_USER_PASS | sudo -S ./dumper.sh; sleep 5'; tmux kill-session -t queue-experiments" Enter
    
    tmux a -t queue-experiments

    echo "Renaming $GENERATOR_PATH/dump.pcap in $GENERATOR_PATH/dump-$i.pcap" >> log.txt
    sshpass -p $GENERATOR_SERVER_USER_PASS ssh $GENERATOR_SERVER_USERNAME@$GENERATOR_SERVER_NAME "mv $GENERATOR_PATH/dump.pcap $GENERATOR_PATH/dump-$i.pcap"

    echo "$(date +'%m-%d-%y-%T') - Cleaning processes..." >> log.txt
    sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME -t "killall -9 run_switchd.sh; killall -9 run_bfshell.sh; killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
    sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME -t "killall -9 run_switchd.sh; killall -9 run_bfshell.sh; killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
    tmux kill-session -t queue-experiments
    
    echo "$(date +'%m-%d-%y-%T') - Reordering ${mcast}x100Gbps ~ End Run ${i}" >> log.txt

    sleep 5
done

sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sudo rm -rf $MULTICAST_PATH/setup_bq_forwarder.py; sudo mv $MULTICAST_PATH/setup_bq_forwarder.py.bak $MULTICAST_PATH/setup_bq_forwarder.py"
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sudo rm -rf $MULTICAST_PATH/pktgen_start_1500.py; sudo mv $MULTICAST_PATH/pktgen_start_1500.py.bak $MULTICAST_PATH/pktgen_start_1500.py"
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $QUEUEMEM_PATH/setup.py; sudo mv $QUEUEMEM_PATH/setup.py.bak $QUEUEMEM_PATH/setup.py"

RESULT_DIR=$path/$slf/$cons_flows

mkdir -p $RESULT_DIR

echo "Copying $GENERATOR_SERVER_NAME pcap in $RESULT_DIR" >> log.txt
sshpass -p $GENERATOR_SERVER_USER_PASS scp -r $GENERATOR_SERVER_USERNAME@$GENERATOR_SERVER_NAME:$GENERATOR_PATH/*.pcap $RESULT_DIR/

echo "Deleting logs from $QUEUEMEM_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $QUEUEMEM_PATH/logs/*"

echo "Deleting logs from $MCAST_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sudo rm -rf $MULTICAST_PATH/logs/*"

echo "Deleting pcaps from $GENERATOR_SERVER_NAME..." >> log.txt
sshpass -p $GENERATOR_SERVER_USER_PASS ssh $GENERATOR_SERVER_USERNAME@$GENERATOR_SERVER_NAME "sudo rm -rf $GENERATOR_PATH/*.pcap"
