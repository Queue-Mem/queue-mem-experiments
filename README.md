# Queue-Mem Experiments

This repository contains the evaluation scripts used to measure Queue-Mem performance.

## Repository Organization

This repository contains:
- `generator`: [FAJITA](https://github.com/FAJITA-Packet-Processing-Framework/FAJITA) elements and scripts used to generate traffic towards a Tofino switch;
- `trex`: scripts and PCAP traces used from the [TRex](https://trex-tgn.cisco.com) experiments;
- `bq_mcast`: different P4 programs to either (i) multicast incoming traffic towards the Queue-Mem switch or (ii) generate and multicast traffic towards the Queue-Mem switch;
- `scripts`: evaluation scripts and results plotter.

Most of the experiments require two Tofino switches (a Tofino2 for Queue-Mem and a Tofino1 for the multicaster), an external server that acts as a traffic generator, and two NF servers. Some experiments (iperf and TRex) require additional servers acting as client/server.

### Traffic Generator

The traffic generator uses [FAJITA](https://github.com/FAJITA-Packet-Processing-Framework/FAJITA).

We used **Ubuntu 20.04.4 LTS** as the Operating System on the server.

First compile and install DPDK, following [this tutorial](https://doc.dpdk.org/guides/prog_guide/build-sdk-meson.html). We used **DPDK 21.08.0**, and it is the only tested version.

After installing DPDK, pull both this repository and FAJITA:

```bash
$ git clone https://github.com/Queue-Mem/queue-mem-experiments.git
$ git clone https://github.com/FAJITA-Packet-Processing-Framework/FAJITA
```

In our testbed, FAJITA has been configured with the following command:
```bash
$ cd FAJITA
$ PKG_CONFIG_PATH=/path/to/dpdk/install/lib/x86_64-linux-gnu/pkgconfig ./configure --enable-dpdk --enable-intel-cpu --verbose --enable-select=poll "CFLAGS=-O3" "CXXFLAGS=-std=c++17 -O3" --disable-dynamic-linking --enable-poll --enable-bound-port-transfer --enable-local --enable-flow --disable-task-stats --enable-cpu-load --enable-dpdk-packet --disable-clone --disable-dpdk-softqueue --enable-research --disable-sloppy --enable-user-timestamp
```
Replace the `PKG_CONFIG_PATH` with the path of your DPDK installation. 

Build the project:
```bash
$ make
```

### TRex

To install TRex, follow the [official guide](https://trex-tgn.cisco.com/trex/doc/trex_manual.html).

### P4 Programs

You need a Tofino to build and run the `bq_mcast`, `bq_forwarder`, and `bq_ecmp` programs. This Tofino switch should be connected with some ports to the Queue-Mem Tofino. The default configuration uses 14 ports.

To build the code, use the following command:
```bash 
./p4_build.sh /path/to/bq_mcast.p4
# or
./p4_build.sh /path/to/bq_forwarder.p4
# or
./p4_build.sh /path/to/bq_ecmp.p4
```

The programs have been tested on **SDE 9.8.0**.

### Scripts

In this folder, you will find both the `bash` scripts to run the paper experiments and a `plot.py` to plot all the figures of the paper. 

The `plot.py` requires `matplotlib`:
```bash
python3 -m pip install matplotlib
```

## Configuration

### Change Ports in `bq_mcast`

To change the ports in the `bq_mcast` program, you need to:
- Change the `port_to_idx` table in both `bq_mcast.p4` and `bq_forwarder.p4`:
```p4
@ternary(1)
table port_to_idx {
    key = {
        eg_intr_md.egress_port: exact;
    }
    actions = {
        assign_idx;
    }
    size = N_MULTICAST;
    const entries = {
        60: assign_idx(0);
        44: assign_idx(1);
        36: assign_idx(2);
        28: assign_idx(3);
        20: assign_idx(4);
        12: assign_idx(5);
        4: assign_idx(6);
        128: assign_idx(7);
        136: assign_idx(8);
        144: assign_idx(9);
        152: assign_idx(10);
        176: assign_idx(11);
        184: assign_idx(12);
        148: assign_idx(13);
    }
}
```

- Change the `setup*.py` files, for example, the one of `setup_bq_forwarder.py`:
```python3
PORTS = [
    52, 32, 140, # Traffic Gen + NF Ports
    60, 44, 36, 28, 20, 12, 4,
    128, 136, 144, 152, 176, 184, 148
]
```

You then need to recompile the P4 program.

### Configure Test Scripts

You need to define some variables in the `bash` scripts to run the tests.
Copy the `set_env.bash.template` and rename it `set_env.bash`. In the file, you will find the following variables:
- `TOFINO_USERNAME`: the Linux user on both Tofinos;
- `TOFINO_USER_PASS`: the user password on both Tofinos;
- `QUEUEMEM_TOFINO_NAME`: the name/IP of the Tofino where Queue-Mem is installed;
- `MCAST_TOFINO_NAME`: the name/IP of the Tofino where `bq_mcast` is installed;
- `NF_SERVER_USERNAME`: the Linux user on the server used as NF;
- `NF_SERVER_USER_PASS`: the user password on the server used as NF;
- `NF_SERVER_NAME_1`: the name/IP of the first server used as NF;
- `NF_SERVER_NAME_2`: the name/IP of the second server used as NF;
- `IPERF_SERVER_NAME_1`: the name/IP of the server used as iPerf Server;
- `IPERF_CLIENT_NAME_1`: the name/IP of the server used as iPerf Client;
- `GENERATOR_SERVER_USERNAME`: the Linux user on the server used as traffic generator;
- `GENERATOR_SERVER_USER_PASS`: the user password on the server used as traffic generator;
- `GENERATOR_SERVER_NAME`: the name/IP of the first server used as traffic generator;
- `CLICK_CORES`: number of threads used by Click/FAJITA;
- `CLICK_DEVICE`: the PCIe address of the NIC used by Click/FAJITA;
- `CLICK_EXECUTABLE`: the absolute path to the `click` executable used by Click/FAJITA;
- `QUEUEMEM_PATH`: path in the Tofino to the Queue-Mem code and `setup.py` file;
- `FWD_PATH`: path in the Tofino to the `bq_forwarder` code and `setup_bq_forwarder.py` file;
- `MULTICAST_PATH`: path in the Tofino to the `bq_mcast` code and `setup_bq_mcast.py` file;
- `NF_PATH`: path in the server where the FAJITA scripts are located;
- `GENERATOR_PATH`: path in the server where the FastClick scripts contained in the `generator` folder are located;
- `TREX_PATH`: path in the server where the TRex bin is located;
- `TREX_CONFIG_PATH`: path in the server where the TRex scripts contained in the `trex` folder are located;
- `MULTICAST_TOFINO_SDE`: SDE path in the Tofino where `bq_mcast` is installed;
- `QUEUEMEM_TOFINO_SDE`: SDE path in the Tofino where Queue-Mem is installed.

## Run The Experiments

After configuring the project, you can run all the experiments by typing the following command:
```bash
sh run_all_experiments.sh -d <results_path> -n <n_of_runs>
```

You can also run a single experiment by running the specific `N_run_experiment_*.sh` file. 

Check the content of the file for the specific parameters to pass.

## Plotting the results

After you gathered all the results, you can plot them by running the following command:
```bash
python3 plot.py <results_path> <figures_path> <mcast>
```