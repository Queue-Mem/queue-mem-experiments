#!/bin/bash

source ../scripts/set_env.bash

$CLICK_EXECUTABLE --dpdk -l $CLICK_CORES -a $CLICK_DEVICE -- gen-mawi.click $@
