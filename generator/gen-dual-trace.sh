#!/bin/bash

$CLICK_EXECUTABLE --dpdk -l $CLICK_CORES -a $CLICK_DEVICE -- gentest-8-dual.click $@
