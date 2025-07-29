#!/bin/bash

source set_env.bash

while getopts p:m:n:l: flag
do
    case "${flag}" in
        p) path=${OPTARG};;
        m) mcast=${OPTARG};;
        n) name=${OPTARG};;
    esac
done

if [ -z "$path" ] || [ -z "$mcast" ] || [ -z "$name" ]; then
        echo 'You missed some parameters' >&2
        exit 1
fi

echo "$(date +'%m-%d-%y-%T') - Starting experiments with the following parameters: " > log.txt

echo "  Output Directory: $path" >> log.txt
echo "  Number Of Mulicast: $mcast" >> log.txt
echo "  Trace Name: $name" >> log.txt

if [[ "$name" == "caida" ]]
then
    TRACE_FILE="gen-trace.sh"
else
    echo "Trace name $name is invalid" >&2
    exit 1
fi

echo "$(date +'%m-%d-%y-%T') - Deleting logs from $QUEUEMEM_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $QUEUEMEM_PATH/logs/*"
echo "$(date +'%m-%d-%y-%T') - Deleting logs from $MCAST_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sudo rm -rf $MULTICAST_PATH/logs/*"

echo "$(date +'%m-%d-%y-%T') - Cleaning processes..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME -t "sudo killall -9 run_switchd.sh; sudo killall -9 run_bfshell.sh; sudo killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME -t "sudo killall -9 run_switchd.sh; sudo killall -9 run_bfshell.sh; sudo killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
tmux kill-session -t queue-experiments

echo "Setting MULTICAST=$mcast" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "mv $MULTICAST_PATH/setup_bq_mcast.py $MULTICAST_PATH/setup_bq_mcast.py.bak; sed 's/N_MULTICAST = .*/N_MULTICAST = $mcast/g' $MULTICAST_PATH/setup_bq_mcast.py.bak > $MULTICAST_PATH/setup_bq_mcast.py"

echo "Setting PRINT_PER_TYPE_TP=True" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sed -i 's/PRINT_PER_TYPE_TP = .*/PRINT_PER_TYPE_TP = True/g' $MULTICAST_PATH/setup_bq_mcast.py"
echo "Setting PRINT_LATENCY=False" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sed -i 's/PRINT_LATENCY = .*/PRINT_LATENCY = False/g' $MULTICAST_PATH/setup_bq_mcast.py"

echo "Setting BG_TRAFFIC_TPUT=True" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "mv $QUEUEMEM_PATH/setup.py $QUEUEMEM_PATH/setup.py.bak; sed 's/BG_TRAFFIC_TPUT = .*/BG_TRAFFIC_TPUT = True/g' $QUEUEMEM_PATH/setup.py.bak > $QUEUEMEM_PATH/setup.py"
echo "Setting DEFAULT_N_PAYLOADS=20" >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sed -i 's/DEFAULT_N_PAYLOADS = .*/DEFAULT_N_PAYLOADS = 20/g' $QUEUEMEM_PATH/setup.py"

sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_1 -t "mkdir -p $GENERATOR_PATH/iperf-logs"

sleep 2
for i in 1 2 3 4 5 6 7 8 9 10
do
    echo "$(date +'%m-%d-%y-%T') - iperf BG Traffic ${mcast}x100Gbps ~ Start Run ${i}" >> log.txt

    tmux kill-session -t queue-experiments
    tmux new-session -d -s queue-experiments

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME SDE=$MULTICAST_TOFINO_SDE SDE_INSTALL=$MULTICAST_TOFINO_SDE_INSTALL '$MULTICAST_TOFINO_SDE/run_switchd.sh -p bq_mcast'" Enter

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME SDE=$MULTICAST_TOFINO_SDE SDE_INSTALL=$MULTICAST_TOFINO_SDE_INSTALL '$MULTICAST_TOFINO_SDE/run_bfshell.sh -i -b $MULTICAST_PATH/setup_bq_mcast.py'" Enter
    
    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME SDE=$QUEUEMEM_TOFINO_SDE SDE_INSTALL=$QUEUEMEM_TOFINO_SDE_INSTALL '$QUEUEMEM_TOFINO_SDE/run_switchd.sh --arch tf2 -p queuemem'" Enter

    tmux select-pane -t 0
    tmux split-window -v -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME SDE=$QUEUEMEM_TOFINO_SDE SDE_INSTALL=$QUEUEMEM_TOFINO_SDE_INSTALL '$QUEUEMEM_TOFINO_SDE/run_bfshell.sh -i -b $QUEUEMEM_PATH/setup.py'" Enter
    
    tmux select-pane -t 0
    tmux split-window -h -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_2 -t 'echo sleep; sleep 37; sudo ip neigh del 192.168.4.135 dev cx7_1; sudo ip neigh add 192.168.4.135 lladdr a0:88:c2:f4:ce:3a dev cx7_1; iperf3 -s -p 5201 & iperf3 -s -p 5202 & iperf3 -s -p 5203 & iperf3 -s -p 5204 & iperf3 -s -p 5205 & iperf3 -s -p 5206 & iperf3 -s -p 5207 & iperf3 -s -p 5208 & iperf3 -s -p 5209 & iperf3 -s -p 5210 & iperf3 -s -p 5211 & iperf3 -s -p 5212 & iperf3 -s -p 5213 & iperf3 -s -p 5214;'" Enter

    tmux select-pane -t 0
    tmux split-window -h -t queue-experiments
    tmux send-keys -t queue-experiments "sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_1 -t 'mkdir -p $GENERATOR_PATH/iperf-logs/$i; echo sleep; sleep 38; sudo ip neigh del 192.168.4.136 dev cx7_0; sudo ip neigh add 192.168.4.136 lladdr a0:88:c2:f4:ce:0a dev cx7_0; iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_1.json -p 5201 & iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_2.json -p 5202 & iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_3.json -p 5203 & iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_4.json -p 5204 & iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_5.json -p 5205 & iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_6.json -p 5206 & iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_7.json -p 5207 &iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_8.json -p 5208 & iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_9.json -p 5209 & iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_10.json -p 5210 & iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_11.json -p 5211 & iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_12.json -p 5212 & iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_13.json -p 5213 & iperf3 -c 192.168.4.136 -b 7.14G -Z --repeating-payload -t 22 -J --logfile $GENERATOR_PATH/iperf-logs/$i/iperf_iperf_14.json -p 5214; sleep 5'; tmux kill-session -t queue-experiments" Enter
    
    tmux select-pane -t 0
    tmux send-keys -t queue-experiments "sshpass -p $GENERATOR_SERVER_USER_PASS ssh $GENERATOR_SERVER_USERNAME@$GENERATOR_SERVER_NAME -t 'echo sleep; sleep 45; cd $GENERATOR_PATH && echo $GENERATOR_SERVER_USER_PASS | sudo -S ./$TRACE_FILE'" Enter
    
    tmux a -t queue-experiments

    echo "$(date +'%m-%d-%y-%T') - Cleaning processes..." >> log.txt
    sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME -t "killall -9 run_switchd.sh; killall -9 run_bfshell.sh; killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
    sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME -t "killall -9 run_switchd.sh; killall -9 run_bfshell.sh; killall -9 bfshell; sudo pkill -9 -f 'bf_switchd'"
    sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_2 -t "killall -9 iperf3"
    tmux kill-session -t queue-experiments
    
    echo "$(date +'%m-%d-%y-%T') - iperf BG Traffic ${mcast}x100Gbps ~ End Run ${i}" >> log.txt

    sleep 5
done

sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sudo rm -rf $MULTICAST_PATH/setup_bq_mcast.py; sudo mv $MULTICAST_PATH/setup_bq_mcast.py.bak $MULTICAST_PATH/setup_bq_mcast.py"
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $QUEUEMEM_PATH/setup.py; sudo mv $QUEUEMEM_PATH/setup.py.bak $QUEUEMEM_PATH/setup.py"

RESULT_DIR=$path/$mcast

mkdir -p $RESULT_DIR/tofino2-logs
mkdir -p $RESULT_DIR/tofino32p-logs

echo "Copying $QUEUEMEM_TOFINO_NAME logs in $RESULT_DIR" >> log.txt
sshpass -p $TOFINO_USER_PASS scp -r $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME:$QUEUEMEM_PATH/logs/* $RESULT_DIR/tofino2-logs

echo "Copying $MCAST_TOFINO_NAME logs in $RESULT_DIR" >> log.txt
sshpass -p $TOFINO_USER_PASS scp -r $TOFINO_USERNAME@$MCAST_TOFINO_NAME:$MULTICAST_PATH/logs/* $RESULT_DIR/tofino32p-logs

echo "Copying $NF_SERVER_NAME_1 logs in $RESULTS_DIR" >> log.txt
sshpass -p $NF_SERVER_USER_PASS scp -r $NF_SERVER_USERNAME@$NF_SERVER_NAME_1:$GENERATOR_PATH/iperf-logs/ $RESULT_DIR/iperf-logs/

echo "Deleting logs from $QUEUEMEM_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$QUEUEMEM_TOFINO_NAME "sudo rm -rf $QUEUEMEM_PATH/logs/*"

echo "Deleting logs from $MCAST_TOFINO_NAME..." >> log.txt
sshpass -p $TOFINO_USER_PASS ssh $TOFINO_USERNAME@$MCAST_TOFINO_NAME "sudo rm -rf $MULTICAST_PATH/logs/*"

echo "Deleting logs from $NF_SERVER_NAME_1..." >> log.txt
sshpass -p $NF_SERVER_USER_PASS ssh $NF_SERVER_USERNAME@$NF_SERVER_NAME_1 "sudo rm -rf $GENERATOR_PATH/iperf-logs"
