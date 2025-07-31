import csv
import math
import operator
import os
import socket
import statistics
import sys
import json

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from functools import partial
from multiprocessing import Pool, cpu_count
from sortedcontainers import SortedDict

figures_path = "figures"


def parse_tofino_logs(directory, metric, skip_null=True):
    data = []

    for item in sorted(filter(lambda i: not i.startswith("."), os.listdir(directory))):
        item_data = []
        full_path = os.path.join(directory, item)
        with open(full_path, "r") as log_file:
            content = log_file.readlines()

        for row in content:
            if not ("MCAST" in row or "QUEUE" in row):
                continue

            row = row.strip()

            (_, ts, _, met_val) = row.split('-')
            (met, val, unit) = met_val.split(' ')
            try:
                ts = float(ts)
                val = float(val)

                if met == metric:
                    if (skip_null and val != 0.0) or not skip_null:
                        item_data.append((ts, val))
            except ValueError:
                # Not a number
                if met == metric:
                    item_data.append((ts, val))

        data.append(sorted(item_data, key=lambda x: x[0]))
    return data


def plot_throughput_gbps_line(directory, ax, color, errorbar_color, linestyle, marker):
    to_plot = {'x': [], 'y': [], 'dx': [], 'min_y': [], 'max_y': []}

    for mcast in sorted(filter(lambda i: not i.startswith("."), os.listdir(directory)), key=lambda x: int(x)):
        folder = os.path.join(directory, mcast, "tofino32p-logs")
        throughput_input_results = list(
            map(lambda x: [y[1] for y in x][1:-2], parse_tofino_logs(folder, "MC_SENT_PPS"))
        )
        throughput_output_results = list(
            map(lambda x: list(filter(lambda z: z > 50000, [y[1] for y in x]))[1:-2],
                parse_tofino_logs(folder, "MC_RCV_BPS"))
        )

        throughput_input_results = list(
            map(lambda x: statistics.mean(x), throughput_input_results)
        )
        throughput_output_results = list(
            map(lambda x: statistics.mean(x), throughput_output_results)
        )

        if throughput_input_results and throughput_output_results:
            to_plot['x'].append(statistics.mean(throughput_input_results) / 1000000)
            to_plot['y'].append(statistics.mean(throughput_output_results) / 1000000000000)
            to_plot['dx'].append(statistics.stdev(throughput_input_results) / 1000000)
            to_plot['min_y'].append(min(throughput_output_results) / 1000000000000)
            to_plot['max_y'].append(max(throughput_output_results) / 1000000000000)

    ax.plot(to_plot['x'], to_plot['y'], linestyle=linestyle, fillstyle='none', color=color, marker=marker)

    for idx, x in enumerate(to_plot['x']):
        ax.errorbar(
            x, to_plot['y'][idx],
            xerr=to_plot['dx'][idx],
            yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                  [to_plot['max_y'][idx] - to_plot['y'][idx]]],
            color=errorbar_color, elinewidth=1,
            capsize=1
        )


def plot_throughput_pps_line(directory, ax, color, errorbar_color, linestyle, marker):
    to_plot = {'x': [], 'y': [], 'dx': [], 'min_y': [], 'max_y': []}

    for mcast in sorted(filter(lambda i: not i.startswith("."), os.listdir(directory)), key=lambda x: int(x)):
        folder = os.path.join(directory, mcast, "tofino32p-logs")
        throughput_input_results = list(
            map(lambda x: [y[1] for y in x][1:-2], parse_tofino_logs(folder, "MC_SENT_PPS"))
        )
        throughput_output_results = list(
            map(lambda x: list(filter(lambda z: z > 50000, [y[1] for y in x]))[1:-2],
                parse_tofino_logs(folder, "MC_RCV_PPS"))
        )

        throughput_input_results = list(
            map(lambda x: statistics.mean(x), throughput_input_results)
        )
        throughput_output_results = list(
            map(lambda x: statistics.mean(x), throughput_output_results)
        )

        if throughput_input_results and throughput_output_results:
            to_plot['x'].append(statistics.mean(throughput_input_results) / 1000000)
            to_plot['y'].append(statistics.mean(throughput_output_results) / 1000000)
            to_plot['dx'].append(statistics.stdev(throughput_input_results) / 1000000)
            to_plot['min_y'].append(min(throughput_output_results) / 1000000)
            to_plot['max_y'].append(max(throughput_output_results) / 1000000)

    ax.plot(to_plot['x'], to_plot['y'], linestyle=linestyle, fillstyle='none', color=color, marker=marker)

    for idx, x in enumerate(to_plot['x']):
        ax.errorbar(
            x, to_plot['y'][idx],
            xerr=to_plot['dx'][idx],
            yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                  [to_plot['max_y'][idx] - to_plot['y'][idx]]],
            color=errorbar_color, elinewidth=1, capsize=1
        )


def plot_throughput_gbps_figure(results_path, name, legend_names):
    global figures_path

    def plot_baseline_gbps_lines(directory, ax):
        to_plot = {'x': [], 'y': [], 'dx': [], 'dy': []}
        to_plot_2 = {'x': [], 'y': [], 'dx': [], 'dy': []}

        for mcast in sorted(filter(lambda i: not i.startswith("."), os.listdir(directory)), key=lambda x: int(x)):
            folder = os.path.join(directory, mcast, "tofino32p-logs")
            throughput_input_results = list(
                map(lambda x: [y[1] for y in x][1:-2], parse_tofino_logs(folder, "MC_SENT_PPS"))
            )
            throughput_input_results = list(
                map(lambda x: statistics.mean(x), throughput_input_results))

            if throughput_input_results:
                to_plot['x'].append(statistics.mean(throughput_input_results) / 1000000)
                to_plot['y'].append(0.1)
                to_plot_2['x'].append(statistics.mean(throughput_input_results) / 1000000)
                to_plot_2['y'].append(0.1125)

        ax.plot(to_plot['x'], to_plot['y'], linestyle="dashed", fillstyle='none', color="gray", marker="^")
        ax.plot(to_plot_2['x'], to_plot_2['y'], linestyle="dotted", fillstyle='none', color="orange", marker="v")

    def plot_baseline_pps_lines(directory, ax):
        to_plot = {'x': [], 'y': [], 'dx': [], 'dy': []}
        to_plot_2 = {'x': [], 'y': [], 'dx': [], 'dy': []}

        for mcast in sorted(filter(lambda i: not i.startswith("."), os.listdir(directory)), key=lambda x: int(x)):
            folder = os.path.join(directory, mcast, "tofino32p-logs")
            throughput_input_results = list(
                map(lambda x: [y[1] for y in x][1:-2], parse_tofino_logs(folder, "MC_SENT_PPS"))
            )
            throughput_input_results = list(
                map(lambda x: statistics.mean(x), throughput_input_results))
            if throughput_input_results:
                to_plot['x'].append(statistics.mean(throughput_input_results) / 1000000)
                to_plot['y'].append((100000000000 / (1280 * 8)) / 1000000)

                to_plot_2['x'].append(statistics.mean(throughput_input_results) / 1000000)
                to_plot_2['y'].append((112500000000 / (1280 * 8)) / 1000000)

        ax.plot(to_plot['x'], to_plot['y'], linestyle="dashed", fillstyle='none', color="gray", marker="^")
        ax.plot(to_plot_2['x'], to_plot_2['y'], linestyle="dotted", fillstyle='none', color="orange", marker="v")

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    ax = plt.gca()

    # plot_throughput_gbps_line(results_path, ax, 'blue', "darkblue", "dashed", "o")
    # plot_baseline_gbps_lines(results_path, ax)
    plot_throughput_pps_line(results_path, ax, 'blue', "darkblue", "dashed", "o")
    plot_baseline_pps_lines(results_path, ax)

    ax.set_xlim([0, 120])
    plt.xticks([0, 20, 40, 60, 80, 100, 120])
    ax.set_ylim([0, 160])
    plt.yticks([0, 20, 40, 60, 80, 100, 120, 140])

    secax = ax.secondary_yaxis('right')
    secax.set_ylim([0, 160])
    secax.set_yticks(ticks=[0, 20, 40, 60, 80, 100, 120, 140], labels=["%.2f" % (((x * 1_000_000 * 1500 * 8) / 1_000_000_000) / 1000) for x in [0, 20, 40, 60, 80, 100, 120, 140]])
    secax.set_ylabel('Output Throughput\n[Tbps]', rotation=270, labelpad=30, fontproperties={'size': 9})

    plt.xlabel('Input Throughput [Mpps]')
    plt.ylabel('Output Throughput\n[Mpps]', fontproperties={'size': 9})
    
    plt.legend(loc="best", labels=legend_names, labelspacing=0.2, prop={'size': 7})
    plt.savefig(os.path.join(figures_path, name), format="pdf", bbox_inches='tight')


def plot_throughput_gbps_figure_nf(results_path, name, legend_names):
    global figures_path

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    ax = plt.gca()

    plot_throughput_pps_line(
        os.path.join(results_path, "fc_lb_rl"), ax, 'blue', "darkblue", "dashed", "o"
    )
    plot_throughput_pps_line(
        os.path.join(results_path, "lb_aes"), ax, 'green', "darkgreen", "dashed", "^"
    )

    ax.set_xlim([0, 110])
    plt.xticks([0, 20, 40, 60, 80, 100])
    ax.set_ylim([0, 110])
    plt.yticks([0, 20, 40, 60, 80, 100])

    secax = ax.secondary_yaxis('right')
    secax.set_ylim([0, 130])
    secax.set_yticks(ticks=[0, 20, 40, 60, 80, 100, 120], labels=["%.2f" % (((x * 1_000_000 * 1500 * 8) / 1_000_000_000) / 1000) for x in [0, 20, 40, 60, 80, 100, 120]])
    secax.set_ylabel('Output Throughput\n[Tbps]', rotation=270, labelpad=30, fontproperties={'size': 9})

    plt.xlabel('Input Throughput [Mpps]')
    plt.ylabel('Output Throughput\n[Mpps]', fontproperties={'size': 9})

    plt.legend(loc="best", labels=legend_names, labelspacing=0.2, prop={'size': 8})
    plt.savefig(os.path.join(figures_path, name), format="pdf", bbox_inches='tight')


def plot_latency_figure_nf(results_path):
    global figures_path

    def plot_latency_line(directory, color, label, errorbar_color):
        to_plot = {'x': [], 'y': [], 'dy': []}

        for rate in sorted(os.listdir(directory), key=lambda x: int(x)):
            folder_32 = os.path.join(directory, rate, "tofino32p-logs")

            throughput_input_results = list(
                map(lambda x: statistics.mean([y[1] for y in x][1:-2]), parse_tofino_logs(folder_32, "MC_SENT_PPS"))
            )

            median_latencies = list(
                map(lambda x: statistics.mean([y[1] for y in x]), parse_tofino_logs(folder_32, "AVG_LATENCY"))
            )

            if throughput_input_results and median_latencies:
                to_plot['x'].append(statistics.mean(throughput_input_results) / 1000000)
                to_plot['y'].append(statistics.mean(median_latencies))
                to_plot['dy'].append(statistics.stdev(median_latencies))

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle='dashed', fillstyle='none', color=color, marker='o')

        for idx, x in enumerate(to_plot['x']):
            plt.errorbar(x, to_plot['y'][idx], yerr=to_plot['dy'][idx], color=errorbar_color, elinewidth=1, capsize=1)

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    plot_latency_line(os.path.join(results_path, "fc_lb_rl"), 'blue', "FC+LB+Per-Flow RL", "darkblue")
    plot_latency_line(os.path.join(results_path, "lb_aes"), 'green', "LB+AES", "darkgreen")

    ax = plt.gca()
    ax.set_xlim([0, 120])
    plt.xticks([0, 20, 40, 60, 80, 100, 120])

    plt.xlabel('Input Throughput [Mpps]')
    plt.ylabel('Median Latency [us]')
    plt.legend(loc="best", labelspacing=0.2, prop={'size': 8})
    plt.savefig(os.path.join(figures_path, f"latency_nf.pdf"), format="pdf", bbox_inches='tight')


def plot_drop_figure(results_path, name, ylim):
    global figures_path

    def plot_drop_line(directory, color, errorbar_color):
        to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}

        for mcast in sorted(filter(lambda i: not i.startswith("."), os.listdir(directory)), key=lambda x: int(x)):
            folder_32 = os.path.join(directory, mcast, "tofino32p-logs")
            folder_tofino2 = os.path.join(directory, mcast, "tofino2-logs")

            throughput_input_results = list(
                map(lambda x: [y[1] for y in x][1:-2], parse_tofino_logs(folder_32, "MC_SENT_BPS"))
            )
            throughput_input_results = list(
                map(lambda x: statistics.mean(x), throughput_input_results)
            )

            dropped_payloads = list(
                map(
                    lambda x: [y[1] for y in x][-min(len(x), 3)] if x else 0,
                    parse_tofino_logs(folder_tofino2, "DROPPED_PAYLOADS")
                )
            )
            input_packets = list(
                map(
                    lambda x: [y[1] for y in x][-min(len(x), 3)] if x else 0,
                    parse_tofino_logs(folder_tofino2, "INPUT_PKTS")
                )
            )

            drop_percentages = list(map(operator.truediv, dropped_payloads, input_packets))

            if throughput_input_results and drop_percentages:
                to_plot['x'].append(statistics.mean(throughput_input_results) / 1000000000000)
                to_plot['y'].append(statistics.mean(drop_percentages) * 100)
                to_plot['min_y'].append(min(drop_percentages) * 100)
                to_plot['max_y'].append(max(drop_percentages) * 100)

        plt.plot(to_plot['x'], to_plot['y'], linestyle='dashed', fillstyle='none', color=color, marker='o')

        for idx, x in enumerate(to_plot['x']):
            plt.errorbar(
                x, to_plot['y'][idx],
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                      [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    plot_drop_line(results_path, 'blue', "darkblue")

    ax = plt.gca()
    ax.set_xlim([0, 1.4])
    plt.xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2])
    ax.set_ylim([0, ylim])

    plt.xlabel('Input Throughput\n[Tbps]')
    plt.ylabel('Payload Drops [%]')
    plt.savefig(os.path.join(figures_path, name), format="pdf", bbox_inches='tight')


def plot_buffer_figure(results_path, name):
    global figures_path

    def plot_buffer_line(directory, color, errorbar_color):
        to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}

        for mcast in sorted(filter(lambda i: not i.startswith("."), os.listdir(directory)), key=lambda x: int(x)):
            folder_32 = os.path.join(directory, mcast, "tofino32p-logs")
            folder_tofino2 = os.path.join(directory, mcast, "tofino2-logs")

            throughput_input_results = list(
                map(lambda x: [y[1] for y in x][1:-2], parse_tofino_logs(folder_32, "MC_SENT_BPS"))
            )
            throughput_input_results = list(
                map(lambda x: statistics.mean(x), throughput_input_results)
            )

            buffer_occupancy = list(
                map(
                    lambda x: [y[1] for y in x][-min(len(x), 3)] if x else 0,
                    parse_tofino_logs(folder_tofino2, "DEQ_QDEPTH_AVG_MB")
                )
            )

            if throughput_input_results and buffer_occupancy:
                to_plot['x'].append(statistics.mean(throughput_input_results) / 1000000000000)
                to_plot['y'].append(statistics.mean(buffer_occupancy))
                to_plot['min_y'].append(min(buffer_occupancy))
                to_plot['max_y'].append(max(buffer_occupancy))

        plt.plot(to_plot['x'], to_plot['y'], linestyle='dashed', fillstyle='none', color=color, marker='o')

        for idx, x in enumerate(to_plot['x']):
            plt.errorbar(
                x, to_plot['y'][idx],
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                      [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    plot_buffer_line(results_path, 'blue', "darkblue")

    ax = plt.gca()
    ax.set_xlim([0, 1.5])
    plt.xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4])

    plt.xlabel('Input Throughput [Tbps]')
    plt.ylabel('Buffer Occupancy [MB]')
    plt.savefig(os.path.join(figures_path, name), format="pdf", bbox_inches='tight')


def plot_latency_figure(results_path):
    global figures_path

    def plot_latency_line(directory, color, label, errorbar_color):
        to_plot = {'x': [], 'y': [], 'dy': []}

        for rate in sorted(os.listdir(directory), key=lambda x: int(x)):
            folder_32 = os.path.join(directory, rate, "tofino32p-logs")

            throughput_input_results = list(
                map(lambda x: statistics.mean([y[1] for y in x][1:-2]), parse_tofino_logs(folder_32, "MC_SENT_BPS"))
            )
            median_latencies = list(
                map(lambda x: statistics.mean([y[1] for y in x]), parse_tofino_logs(folder_32, "AVG_LATENCY"))
            )

            if throughput_input_results and median_latencies:
                to_plot['x'].append(statistics.mean(throughput_input_results) / 1000000000)
                to_plot['y'].append(statistics.mean(median_latencies))
                to_plot['dy'].append(statistics.stdev(median_latencies))

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle='dashed', fillstyle='none', color=color, marker='o')

        for idx, x in enumerate(to_plot['x']):
            plt.errorbar(x, to_plot['y'][idx], yerr=to_plot['dy'][idx], color=errorbar_color, elinewidth=1, capsize=1)

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    plot_latency_line(os.path.join(results_path, "baseline"), 'blue', "Baseline", "darkblue")
    plot_latency_line(os.path.join(results_path, "jammer"), 'green', "Queue-Mem", "darkgreen")

    ax = plt.gca()
    ax.set_xlim([0, 100])
    plt.xticks([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100], rotation=90)
    ax.set_ylim([0, 50])

    plt.xlabel('Input Throughput [Gbps]')
    plt.ylabel('Median Latency [us]')
    plt.legend(loc="best", labelspacing=0.2, prop={'size': 8})
    plt.savefig(os.path.join(figures_path, f"latency.pdf"), format="pdf", bbox_inches='tight')


def plot_variable_throughput_figure(results_path, xlim, xtick, to_skip_tp, to_skip_buf, to_skip_lat, name, include_fwd=True, include_lat=True, include_axis=True):
    global figures_path

    def plot_variable_throughput_line(ax, directory, metric, label, color, errorbar_color, marker):
        to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}

        folder_32 = os.path.join(directory.format(name="queuemem"), "tofino32p-logs")
        
        results = list(map(lambda x: [y for y in x][:-to_skip_tp] if to_skip_tp > 0 else [y for y in x], parse_tofino_logs(folder_32, metric)))
        results = list(map(lambda x: [y for y in x if y[1] >= 10000000000], results))
        results_per_ts = SortedDict({})
        for result in results:
            start_ts = result[0][0]

            for ts, val in result:
                ts_point = int(ts - start_ts)

                if ts_point not in results_per_ts:
                    results_per_ts[ts_point] = []

                results_per_ts[ts_point].append(val)

        results_avg = SortedDict({})
        results_min = SortedDict({})
        results_max = SortedDict({})

        for time, values in results_per_ts.items():
            if len(values) <= 1:
                continue

            results_avg[time] = statistics.mean(values)
            results_min[time] = min(values)
            results_max[time] = max(values)

        if results_avg:
            for time, v in results_avg.items():
                to_plot['x'].append(time)
                to_plot['y'].append(v / 1000000000000)
                to_plot['min_y'].append(results_min[time] / 1000000000000)
                to_plot['max_y'].append(results_max[time] / 1000000000000)

        ax.plot(
            to_plot['x'], to_plot['y'],
            label=label, linestyle='dashed', fillstyle='none', color=color, marker=marker
        )

        for idx, x in enumerate(to_plot['x']):
            ax.errorbar(
                x, to_plot['y'][idx],
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                      [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

        return to_plot

    def plot_variable_throughput_latency_line(ax, directory, metric, label, color, errorbar_color, marker):
        to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}

        folder_32 = os.path.join(directory.format(name="queuemem"), "tofino32p-logs")
        
        results = list(map(lambda x: [y for y in x][:-to_skip_lat] if to_skip_lat > 0 else [y for y in x], parse_tofino_logs(folder_32, metric)))
        results_per_ts = SortedDict({})
        for result in results:
            start_ts = result[0][0]

            for ts, val in result:
                ts_point = int(ts - start_ts)

                if ts_point not in results_per_ts:
                    results_per_ts[ts_point] = []

                results_per_ts[ts_point].append(val)

        results_avg = SortedDict({})
        results_min = SortedDict({})
        results_max = SortedDict({})

        for time, values in results_per_ts.items():
            results_avg[time] = statistics.mean(values)
            results_min[time] = min(values)
            results_max[time] = max(values)

        if results_avg:
            for time, v in results_avg.items():
                if time > xlim:
                    continue

                to_plot['x'].append(time)
                to_plot['y'].append(v)
                to_plot['min_y'].append(results_min[time])
                to_plot['max_y'].append(results_max[time])

        ax.plot(
            to_plot['x'], to_plot['y'],
            label=label, linestyle='dashed', fillstyle='none', color=color, marker=marker
        )

        for idx, x in enumerate(to_plot['x']):
            ax.errorbar(
                x, to_plot['y'][idx],
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                      [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

        return to_plot
    
    def plot_variable_throughput_buffer_line(ax, directory, label, color, errorbar_color, marker):
        to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}

        # Get Tofino32p timestamps
        folder_32 = os.path.join(directory, "tofino32p-logs")
        tstamps = list(
            map(
                lambda x: [int(y[0]) for y in x][:-to_skip_buf] if to_skip_buf > 0 else [int(y[0]) for y in x],
                parse_tofino_logs(folder_32, "MC_SENT_BPS")
            )
        )

        folder_tofino2 = os.path.join(directory, "tofino2-logs")
        results = parse_tofino_logs(folder_tofino2, "DEQ_QDEPTH_AVG_MB", False)
        final_results = []
        for run, result in enumerate(results):
            run_start_ts = tstamps[run][0]
            run_end_ts = tstamps[run][-1]
            filtered_results = [(int(ts - run_start_ts), v) for ts, v in result if int(ts) >= run_start_ts and int(ts) <= run_end_ts]
            final_results.append(filtered_results)

        results_per_ts = SortedDict({})

        for run_results in final_results:
            for time, value in run_results:
                if time not in results_per_ts:
                    results_per_ts[time] = []

                results_per_ts[time].append(value)

        results_avg = SortedDict({})
        results_min = SortedDict({})
        results_max = SortedDict({})

        for time, values in results_per_ts.items():
            results_avg[time] = statistics.mean(values)
            results_min[time] = min(values)
            results_max[time] = max(values)

        if results_avg:
            for ts, v in results_avg.items():
                if ts > xlim:
                    continue
                
                to_plot['x'].append(ts)
                to_plot['y'].append(v)
                to_plot['min_y'].append(results_min[ts])
                to_plot['max_y'].append(results_max[ts])

        ax.plot(
            to_plot['x'], to_plot['y'], linestyle='dashed', fillstyle='none', label=label, color=color, marker=marker
        )

        for idx, x in enumerate(to_plot['x']):
            ax.errorbar(
                x, to_plot['y'][idx],
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                      [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

        return to_plot

    if include_lat:
        fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, figsize=(3, 4), sharex=True)  
    else:
        fig, (ax1, ax2) = plt.subplots(nrows=2, figsize=(3, 4), sharex=True)  

    plt.subplots_adjust(wspace=0.4)

    ax1.grid(linestyle='--', linewidth=0.5)
    ax2.grid(linestyle='--', linewidth=0.5)
    if include_lat:
        ax3.grid(linestyle='--', linewidth=0.5)

    plot_variable_throughput_line(
        ax1, results_path, "MC_SENT_BPS", "Input", 'green', "darkgreen", "o"
    )
    plot_variable_throughput_line(
        ax1, results_path, "MC_RCV_BPS", "Output", 'purple', "rebeccapurple", "^"
    )
    plot_variable_throughput_buffer_line(ax2, results_path.format(name="queuemem"), "Queue-Mem", 'blue', "darkblue", "v")
    if include_fwd:
        plot_variable_throughput_buffer_line(ax2, results_path.format(name="simple_forwarder"), "ECMP-Fwd", 'red', "darkred", "s")

    if include_lat:
        plot_variable_throughput_latency_line(
            ax3, results_path.format(name="queuemem"), "AVG_LATENCY", "P50", 'orange', "darkorange", "^"
        )
        plot_variable_throughput_latency_line(
            ax3, results_path.format(name="queuemem"), "99_LATENCY", "P99", 'brown', "#640f0f", "^"
        )
    
    ax1.set_ylim([0, 1.8])
    ax1.set_yticks([0, 0.4, 0.8, 1.2, 1.6])
    if not include_fwd:
        ax2.set_ylim([0, 3])
        ax2.set_yticks([0, 0.5, 1, 1.5, 2, 2.5, 3])
    else:
        ax2.set_ylim([0, 12])
        ax2.set_yticks([0, 2, 4, 6, 8, 10])
    if include_lat:
        ax3.set_ylim([0, 90])
        ax3.set_yticks([0, 20, 40, 60, 80])

    if 'caida' in name or 'mawi' in name:
        ax1.set_xticks(range(0, xlim + 1, xtick))
        ax2.set_xticks(range(0, xlim + 1, xtick))
        if include_lat:
            ax3.set_xticks(range(0, xlim + 1, xtick))
    else:
        ax1.set_xticks(range(0, xlim + 4, xtick))
        ax2.set_xticks(range(0, xlim + 4, xtick))
        if include_lat:
            ax3.set_xticks(range(0, xlim + 4, xtick))

    if include_axis:
        ax1.set_ylabel('Throughput\n[Tbps]')
        ax2.set_ylabel('Buffer Occupancy\n[MB]')
        if include_lat:
            ax3.set_ylabel('Latency\n[μs]')
    
    if include_lat:
        ax3.set_xlabel('Time [s]')
    else:
        ax2.set_xlabel('Time [s]')

    ax1.legend(loc="upper left", labelspacing=0.2, prop={'size': 8}, ncols=2)
    if include_fwd:
        ax2.legend(loc="upper right", labelspacing=0.2, prop={'size': 8}, ncols=2)
    if include_lat:
        ax3.legend(loc="upper left", labelspacing=0.2, prop={'size': 7.3}, ncols=2)

    plt.savefig(os.path.join(figures_path, name), format="pdf", bbox_inches='tight')


def plot_variable_throughput_drop_figure(results_path, ylim, to_skip, name):
    global figures_path

    def plot_variable_throughput_drop_line(directory, color, errorbar_color):
        to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}

        # Get Tofino32p timestamps
        folder_32 = os.path.join(directory.format(name="queuemem"), "tofino32p-logs")
        tstamps = list(
            map(lambda x: [int(y[0]) for y in x][:-to_skip] if to_skip > 0 else [int(y[0]) for y in x],
                parse_tofino_logs(folder_32, "MC_SENT_BPS"))
        )

        folder_tofino2 = os.path.join(directory.format(name="queuemem"), "tofino2-logs")

        input_pkts_results = parse_tofino_logs(folder_tofino2, "INPUT_PKTS", False)
        dropped_packets_results = parse_tofino_logs(folder_tofino2, "DROPPED_PAYLOADS", False)
        final_input_pkts_results = []
        final_dropped_results = []
        for run, result in enumerate(input_pkts_results):
            run_start_ts = tstamps[run][0]
            run_end_ts = tstamps[run][-1]
            input_pkts = [(ts - run_start_ts, v) for ts, v in result if int(ts) >= run_start_ts and int(ts) <= run_end_ts]

            run_results = []
            for idx, (time, _) in enumerate(input_pkts):
                drop = list(filter(lambda x: x[0] == time, dropped_packets_results[run]))
                run_results.append((time, 0) if not drop else drop.pop())

            final_input_pkts_results.append(input_pkts)
            final_dropped_results.append(run_results)

        drop_percentages = []
        for idx, result in enumerate(final_dropped_results):
            drop_percentages.append(
                list(map(lambda x, y: (int(x[0]), (x[1] / y[1]) * 100 if y[1] > 0 else 0), result, final_input_pkts_results[idx]))
            )

        drop_percentages_per_ts = SortedDict({})

        for run_drop_percentages in drop_percentages:
            for time, value in run_drop_percentages:
                if time not in drop_percentages_per_ts:
                    drop_percentages_per_ts[time] = []

                drop_percentages_per_ts[time].append(value)

        drop_percentages_avg = SortedDict({})
        drop_percentages_min = SortedDict({})
        drop_percentages_max = SortedDict({})

        for time, values in drop_percentages_per_ts.items():
            if len(values) <= 1:
                continue

            drop_percentages_avg[time] = statistics.mean(values)
            drop_percentages_min[time] = min(values)
            drop_percentages_max[time] = max(values)

        if drop_percentages_avg:
            for ts, v in drop_percentages_avg.items():
                to_plot['x'].append(ts)
                to_plot['y'].append(v)
                to_plot['min_y'].append(drop_percentages_min[ts])
                to_plot['max_y'].append(drop_percentages_max[ts])

        plt.plot(to_plot['x'], to_plot['y'], linestyle='dashed', fillstyle='none', color=color, marker='o')

        for idx, x in enumerate(to_plot['x']):
            plt.errorbar(
                x, to_plot['y'][idx],
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                      [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

        return to_plot

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    values = plot_variable_throughput_drop_line(results_path, 'blue', "darkblue")

    ax = plt.gca()
    ax.set_ylim([0, ylim])
    plt.xticks(range(0, values['x'][-1] + 1, 2), rotation=90)

    plt.xlabel('Time [s]')
    plt.ylabel('Payload Drops [%]')
    plt.savefig(os.path.join(figures_path, name), format="pdf", bbox_inches='tight')


def plot_bg_throughput_figure(results_path, to_skip_bg, to_skip_nf, name):
    global figures_path

    def plot_nf_throughput_line(ax, directory, label, color, errorbar_color, marker):
        to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}

        folder_32 = os.path.join(directory, "tofino32p-logs")

        not_split_results = list(map(lambda x: [y for y in x][:-to_skip_nf] if to_skip_nf > 0 else [y for y in x], parse_tofino_logs(folder_32, "NOT_SPLIT_BPS", False)))
        split_results = list(map(lambda x: [y for y in x][:-to_skip_nf] if to_skip_nf > 0 else [y for y in x], parse_tofino_logs(folder_32, "SPLIT_BPS", False)))
        results_per_ts = SortedDict({})
        for run, result in enumerate(split_results):
            result = result[15:]
            start_ts = result[0][0]

            for idx, (ts, val) in enumerate(result):
                ts_point = int(ts - start_ts)

                if ts_point not in results_per_ts:
                    results_per_ts[ts_point] = []

                (_, not_split_val) = not_split_results[run][idx] if idx < len(not_split_results[run]) - 1 else (ts, 0)

                results_per_ts[ts_point].append(val + not_split_val)

        results_avg = SortedDict({})
        results_min = SortedDict({})
        results_max = SortedDict({})

        for time, values in results_per_ts.items():
            results_avg[time] = statistics.mean(values)
            results_min[time] = min(values)
            results_max[time] = max(values)

        if results_avg:
            for time, v in results_avg.items():
                to_plot['x'].append(time)
                to_plot['y'].append(v / 1000000000000)
                to_plot['min_y'].append(results_min[time] / 1000000000000)
                to_plot['max_y'].append(results_max[time] / 1000000000000)

        ax.plot(
            to_plot['x'], to_plot['y'],
            label=label, linestyle='dashed', fillstyle='none', color=color, marker=marker
        )

        for idx, x in enumerate(to_plot['x']):
            ax.errorbar(
                x, to_plot['y'][idx],
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                      [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

        return to_plot

    def plot_bg_throughput_line(ax, directory, metric, label, color, errorbar_color, marker):
        to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}

        folder_32 = os.path.join(directory, "tofino32p-logs")

        results = list(map(lambda x: [y for y in x][:-to_skip_bg], parse_tofino_logs(folder_32, metric, False)))
        results_per_ts = SortedDict({})
        for result in results:
            result = result[15:]
            start_ts = result[0][0]

            for ts, val in result:
                ts_point = int(ts - start_ts)

                if ts_point not in results_per_ts:
                    results_per_ts[ts_point] = []

                results_per_ts[ts_point].append(val)

        results_avg = SortedDict({})
        results_min = SortedDict({})
        results_max = SortedDict({})

        for time, values in results_per_ts.items():
            if len(values) <= 1:
                continue

            results_avg[time] = statistics.mean(values)
            results_min[time] = min(values)
            results_max[time] = max(values)

        if results_avg:
            for time, v in results_avg.items():
                to_plot['x'].append(time)
                to_plot['y'].append(v / 1000000000000)
                to_plot['min_y'].append(results_min[time] / 1000000000000)
                to_plot['max_y'].append(results_max[time] / 1000000000000)

        ax.plot(
            to_plot['x'], to_plot['y'],
            label=label, linestyle='dashed', fillstyle='none', color=color, marker=marker
        )

        for idx, x in enumerate(to_plot['x']):
            ax.errorbar(
                x, to_plot['y'][idx],
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                      [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

    def plot_cwnd_line(ax, directory, color, errorbar_color, marker):
        to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}

        results_per_ts = SortedDict({})

        folder_iperf = os.path.join(directory, "iperf-logs")
        for run in sorted([int(x) for x in os.listdir(folder_iperf)]):
            run_folder = os.path.join(folder_iperf, f"{run}")
            for iperf_file in os.listdir(run_folder):
                iperf_file_path = os.path.join(run_folder, iperf_file)
                with open(iperf_file_path, "r") as run_file:
                    result = json.loads(run_file.read())

                if "intervals" not in result:
                    continue

                for interval in result["intervals"]:
                    stream = interval['streams'][0]

                    ts = int(stream['start'])
                    if ts not in results_per_ts:
                        results_per_ts[ts] = []
                    results_per_ts[ts].append(stream['snd_cwnd'])

        results_avg = SortedDict({})
        results_min = SortedDict({})
        results_max = SortedDict({})
        for time, values in results_per_ts.items()[:-1]:
            results_avg[time] = statistics.mean(values)
            results_min[time] = min(values)
            results_max[time] = max(values)
        
        if results_avg:
            for time, v in results_avg.items():
                to_plot['x'].append(time)
                to_plot['y'].append(v / 1000000)
                to_plot['min_y'].append(results_min[time] / 1000000)
                to_plot['max_y'].append(results_max[time] / 1000000)

        ax.plot(
            to_plot['x'], to_plot['y'],
            linestyle='dashed', fillstyle='none', color=color, marker=marker
        )

        for idx, x in enumerate(to_plot['x']):
            ax.errorbar(
                x, to_plot['y'][idx],
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                      [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

    plt.clf()

    fig, (ax1, ax2) = plt.subplots(nrows=2, figsize=(3, 2), sharex=True)

    plt.subplots_adjust(wspace=0.4)

    ax1.grid(linestyle='--', linewidth=0.5)
    ax2.grid(linestyle='--', linewidth=0.5)

    ax1.sharex(ax2)
    ax1.set_ylim([0, 1.4])
    ax1.set_yticks([0, 0.4, 0.8, 1.2])
    ax2.set_ylim([0, 5])
    ax2.set_yticks([0, 1, 2, 3, 4])

    ax1.set_xlim([0, 22])
    ax2.set_xlim([0, 22])
    ax1.set_xticks(range(0, 24, 4))
    ax2.set_xticks(range(0, 24, 4))

    ax1.set_ylabel('Throughput\n[Tbps]')
    ax2.set_xlabel('Time [s]')
    ax2.set_ylabel('TCP\nCwnd Size\n[MB]')

    plot_bg_throughput_line(
        ax1, results_path, "MC_SENT_BPS", "Input", 'green', "darkgreen", "o"
    )
    plot_bg_throughput_line(
        ax1, results_path, "BG_BPS", "TCP Traffic", 'blue', "darkblue", "s"
    )
    plot_nf_throughput_line(
        ax1, results_path, "NF Traffic", 'red', "darkred", "^"
    )
    plot_cwnd_line(ax2, results_path, 'blue', 'darkblue', "s")

    ax1.legend(loc="upper right", labelspacing=0.2, bbox_to_anchor=(1.47, 1.05), prop={'size': 8}, ncols=1)

    plt.savefig(os.path.join(figures_path, name), format="pdf", bbox_inches='tight')


def plot_bg_latency_figure(results_path, to_skip):
    global figures_path

    def plot_latency_line(directory, metric, color, label, marker, errorbar_color):
        to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}

        folder_32 = os.path.join(directory, "tofino32p-logs")

        results = list(map(lambda x: [y for y in x][:-to_skip] if to_skip > 0 else [y for y in x], parse_tofino_logs(folder_32, metric)))
        results_per_ts = SortedDict({})
        for result in results:
            result = result[1:]
            start_ts = result[0][0]

            for ts, val in result:
                ts_point = int(ts - start_ts)

                if ts_point not in results_per_ts:
                    results_per_ts[ts_point] = []

                results_per_ts[ts_point].append(val)
        
        results_avg = SortedDict({})
        results_min = SortedDict({})
        results_max = SortedDict({})

        for time, values in results_per_ts.items():
            results_avg[time] = statistics.mean(values)
            results_min[time] = min(values)
            results_max[time] = max(values)

        if results_avg:
            for time, v in results_avg.items():
                to_plot['x'].append(time)
                to_plot['y'].append(v)
                to_plot['min_y'].append(results_min[time])
                to_plot['max_y'].append(results_max[time])

        plt.plot(
            to_plot['x'], to_plot['y'],
            label=label, linestyle='dashed', fillstyle='none', color=color, marker=marker
        )

        for idx, x in enumerate(to_plot['x']):
            plt.errorbar(
                x, to_plot['y'][idx],
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                      [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

        return to_plot

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    plot_latency_line(results_path, 'AVG_LATENCY', 'red', "NF Traffic (split)", "^", "darkred")
    plot_latency_line(results_path, 'AVG_NOT_SPLIT_LATENCY', 'orange', "NF Traffic (unsplit)", "v", "darkorange")
    plot_latency_line(results_path, 'AVG_BG_LATENCY', 'blue', "non-NF Traffic", "s", "darkblue")

    ax = plt.gca()
    plt.xticks(range(0, 8, 2))
    ax.set_ylim([0, 16])
    plt.yticks([0, 2, 4, 6, 8, 10, 12, 14, 16])

    plt.xlabel('Time [s]')
    plt.ylabel('Latency [μs]')
    plt.legend(loc="center right", bbox_to_anchor=(1.65, 0.5), ncols=1, labelspacing=0.2, prop={'size': 8})
    plt.savefig(os.path.join(figures_path, "bg_latency.pdf"), format="pdf", bbox_inches='tight')


def plot_nf_drops_figure(results_path, x_label, x_ticks, y_ticks, name):
    global figures_path

    def plot_nf_drops_line(directory, metric, label, color, errorbar_color, marker):
        to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}

        for drop_perc, drop_rate in sorted([(int((1 / int(x)) * 100) if int(x) > 0 else 0, x) for x in os.listdir(directory)], key=lambda x: int(x[0])):
            folder_32 = os.path.join(directory, str(drop_rate), "tofino32p-logs")

            throughput_results = list(
                map(lambda x: list(filter(lambda z: z > 50000, [y[1] for y in x]))[1:-2], parse_tofino_logs(folder_32, metric))
            )
            throughput_results = list(
                map(lambda x: statistics.mean(x), throughput_results)
            )

            if throughput_results:
                to_plot['x'].append(drop_perc)
                to_plot['y'].append(statistics.mean(throughput_results) / 1000000000000)
                to_plot['min_y'].append(min(throughput_results) / 1000000000000)
                to_plot['max_y'].append(max(throughput_results) / 1000000000000)

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle='dashed', fillstyle='none', color=color, marker=marker)

        for idx, x in enumerate(to_plot['x']):
            plt.errorbar(
                x, 
                to_plot['y'][idx], 
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                      [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1)

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    plot_nf_drops_line(results_path, "MC_SENT_BPS", "Input", 'green', "darkgreen", '^')
    plot_nf_drops_line(results_path, "MC_RCV_BPS", "Output", 'purple', "rebeccapurple", 'o')

    ax = plt.gca()
    plt.yticks(ticks=y_ticks)
    plt.xticks(ticks=x_ticks)

    plt.xlabel(x_label)
    plt.ylabel('Throughput\n[Tbps]')
    plt.legend(loc="best", labelspacing=0.2, prop={'size': 8}, ncols=2)
    plt.savefig(os.path.join(figures_path, name), format="pdf", bbox_inches='tight')


def extract_packet_data_dpkt(pcap_file, total_packets):
    import dpkt

    results = []
    with open(pcap_file, 'rb') as f:
        reader = dpkt.pcap.Reader(f)
        for i, (ts, buf) in enumerate(reader):
            if i == total_packets:
                break

            try:
                eth = dpkt.ethernet.Ethernet(buf)
                if not isinstance(eth.data, dpkt.ip.IP):
                    continue
                ip = eth.data
                if not isinstance(ip.data, dpkt.udp.UDP):
                    continue
                udp = ip.data
                if len(udp.data) < 4:
                    continue
                seq = int.from_bytes(udp.data[:4], byteorder='big')
                flow_id = (
                    socket.inet_ntop(socket.AF_INET, ip.src), udp.sport,
                    socket.inet_ntop(socket.AF_INET, ip.dst), udp.dport
                )
                results.append((flow_id, ts, seq))
            except Exception:
                continue

    return results


def compute_reordering_extent(seq_list):
    extents = []
    for i in range(len(seq_list)):
        s_i = seq_list[i]
        for j in range(i):
            if seq_list[j] > s_i:
                e = i - j
                extents.append(e)
                break
    return extents


def process_flow(packets):
    packets.sort(key=lambda x: x[0])
    seqs = [seq for _, seq in packets]
    return compute_reordering_extent(seqs)


def analyze_single_pcap(pcap_file):
    total_packets = 15000000
    return analyze_pcap(pcap_file, total_packets)


def analyze_pcap(pcap_path, total_packets):
    print(f"=== Analyzing {pcap_path} ===")

    results = extract_packet_data_dpkt(pcap_path, total_packets)

    flows = defaultdict(list)
    for flow_id, ts, seq in results:
        flows[flow_id].append((ts, seq))

    n_flows = len(flows.keys())

    all_extents = []
    for flowid, vals in flows.items():
        extents = process_flow(vals)
        all_extents.extend(extents)

    if not all_extents:
        print(f"No reordered packets found in {pcap_path}.")
        return 0, 0, 0, n_flows

    mean_extent = np.mean(all_extents)
    max_extent = np.max(all_extents)
    perc_reordered = len(all_extents) / len(results) * 100

    return perc_reordered, mean_extent, max_extent, n_flows


def plot_reordering_slf_figure(results_path):
    global figures_path

    to_plot_perc = {'x': [], 'y': [], 'min_y': [], 'max_y': []}
    to_plot_ext = {'x': [], 'y': [], 'min_y': [], 'max_y': []}
    
    def parse_values(directory):
        for slf in sorted(filter(lambda i: not i.startswith("."), os.listdir(directory)), key=lambda x: int(x)):
            folder = os.path.join(directory, slf, "125")
            slf_pcaps = list(map(lambda y: os.path.join(folder, y), filter(lambda i: not i.startswith("."), os.listdir(folder))))
        
            with Pool(processes=min(len(slf_pcaps), cpu_count())) as pool:
                results = pool.map(analyze_single_pcap, slf_pcaps)
            
            perc_y = []
            ext_y = []
            for (perc_reordered, mean_extent, _, n_flows) in results:
                perc_y.append(perc_reordered)
                ext_y.append(mean_extent)
                print("slf", slf, "n_flows", n_flows)

            if perc_y:
                to_plot_perc['x'].append(int(slf))
                to_plot_perc['y'].append(statistics.mean(perc_y))
                to_plot_perc['min_y'].append(min(perc_y))
                to_plot_perc['max_y'].append(max(perc_y))

            if ext_y:
                to_plot_ext['x'].append(int(slf))
                to_plot_ext['y'].append(statistics.mean(ext_y))
                to_plot_ext['min_y'].append(min(ext_y))
                to_plot_ext['max_y'].append(max(ext_y))

    def plot_reorder_perc_line(color, errorbar_color, linestyle, marker):
        plt.plot(to_plot_perc['x'], to_plot_perc['y'], linestyle=linestyle, fillstyle='none', color=color, marker=marker)

        for idx, x in enumerate(to_plot_perc['x']):
            plt.errorbar(
                x, to_plot_perc['y'][idx],
                yerr=[[to_plot_perc['y'][idx] - to_plot_perc['min_y'][idx]],
                    [to_plot_perc['max_y'][idx] - to_plot_perc['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

    def plot_reorder_ext_line(color, errorbar_color, linestyle, marker):
        plt.plot(to_plot_ext['x'], to_plot_ext['y'], linestyle=linestyle, fillstyle='none', color=color, marker=marker)

        for idx, x in enumerate(to_plot_ext['x']):
            plt.errorbar(
                x, to_plot_ext['y'][idx],
                yerr=[[to_plot_ext['y'][idx] - to_plot_ext['min_y'][idx]],
                    [to_plot_ext['max_y'][idx] - to_plot_ext['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

    perc_file = os.path.join(results_path, "reorder_perc.json")
    ext_file = os.path.join(results_path, "reorder_ext.json")
    if os.path.isfile(perc_file) and os.path.isfile(ext_file):
        with open(perc_file, "r") as pf:
            to_plot_perc = json.loads(pf.read())
        with open(ext_file, "r") as ef:
            to_plot_ext = json.loads(ef.read())
    else:
        parse_values(results_path)
        with open(perc_file, "w") as pf:
            pf.write(json.dumps(to_plot_perc))
        with open(ext_file, "w") as ef:
            ef.write(json.dumps(to_plot_ext))

    plt.figure(figsize=(3, 1.3))
    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    plot_reorder_perc_line('blue', "darkblue", "dashed", "s")

    plt.xlabel('Spatial Locality Factor')
    plt.ylabel('Reordered\nPacket Ratio [%]')
    # plt.ticklabel_format(axis='both', style='sci', scilimits=(-3,-2))
    ax = plt.gca()
    ax.set_xlim([0.9, 24])
    ax.set_ylim([0, 0.01])
    ax.set_xscale('log', base=2)
    ax.set_xticks([1, 2, 4, 8, 16, 20], labels=[1, 2, 4, 8, 16, 20], rotation=90)
    ax.set_yticks([0.0, 0.002, 0.004, 0.006, 0.008, 0.010])
    plt.savefig(os.path.join(figures_path, "reorder_perc.pdf"), format="pdf", bbox_inches='tight')

    plt.figure(figsize=(3, 1.3))
    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    plot_reorder_ext_line('blue', "darkblue", "dashed", "s")

    plt.xlabel('Spatial Locality Factor')
    plt.ylabel('Average\nReordering Extent')
    ax = plt.gca()
    ax.set_xlim([0.9, 24])
    ax.set_ylim([0, 11])
    ax.set_xscale('log', base=2)
    ax.set_xticks([1, 2, 4, 8, 16, 20], labels=[1, 2, 4, 8, 16, 20], rotation=90)
    ax.set_yticks(range(0, 14, 2))
    plt.savefig(os.path.join(figures_path, "reorder_ext.pdf"), format="pdf", bbox_inches='tight')


def plot_iperf_full_figure(results_path):
    global figures_path
    
    ts_to_retrans = SortedDict()
    folder_iperf = os.path.join(results_path, "iperf-logs")
    for run in sorted([int(x) for x in os.listdir(folder_iperf)]):
        iperf_file_path = os.path.join(folder_iperf, f"{run}", "iperf.json")
        
        with open(iperf_file_path, "r") as run_file:
            result = json.loads(run_file.read())

        if "intervals" not in result:
            continue

        ts_to_stats = SortedDict()
        for interval in result["intervals"]:
            for stream in interval['streams']:
                ts = int(stream['end'])
                if ts not in ts_to_stats:
                    ts_to_stats[ts] = {'retrans': [], 'pkts': []}
                    
                ts_to_stats[ts]['retrans'].append(stream['retransmits'])
                ts_to_stats[ts]['pkts'].append(stream['bits_per_second'] / (4000 * 8))
            
            total_retransmits = sum(ts_to_stats[ts]['retrans'])
            total_pkts = sum(ts_to_stats[ts]['pkts'])
            perc_reorder = (total_retransmits / total_pkts) * 100
            if ts not in ts_to_retrans:
                ts_to_retrans[ts] = []
            ts_to_retrans[ts].append(perc_reorder)
            
    to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}
    for ts, percs in ts_to_retrans.items():
        to_plot['x'].append(ts)
        to_plot['y'].append(statistics.mean(percs))
        to_plot['min_y'].append(min(percs))
        to_plot['max_y'].append(max(percs))

    def plot_retrans_line(color, errorbar_color, linestyle, marker):
        plt.plot(to_plot['x'], to_plot['y'], linestyle=linestyle, fillstyle='none', color=color, marker=marker)

        for idx, x in enumerate(to_plot['x']):
            plt.errorbar(
                x, to_plot['y'][idx],
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                    [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    plot_retrans_line('blue', "darkblue", "dashed", "s")

    plt.xlabel('Time [s]')
    # plt.ylabel('TCP Retrans. [%]')
    ax = plt.gca()
    ax.set_xlim([0, 11])
    # ax.set_ylim([0, 0.15])
    ax.set_xticks(range(0, 11))
    # ax.set_yticks(np.arange(0, 0.15, 0.02))
    plt.savefig(os.path.join(figures_path, "iperf_retrans.pdf"), format="pdf", bbox_inches='tight')


def plot_trex_figure(results_path, to_skip):
    global figures_path

    def plot_retrans_line(results_path, label, color, errorbar_color, linestyle, marker):
        ts_to_retrans = SortedDict()
        ts_to_pkts = SortedDict()
        for run in sorted([int(x.replace('.json', '')) for x in os.listdir(results_path)]):
            trex_file_path = os.path.join(results_path, f"{run}.json")
            
            with open(trex_file_path, "r") as run_file:
                result = json.loads(run_file.read())

            first_ts = float(list(result.keys())[to_skip])

            for t, vals in list(result.items())[to_skip:]:
                ts = int(float(t) - first_ts)
                if ts not in ts_to_retrans:
                    ts_to_retrans[ts] = []
                if ts not in ts_to_pkts:
                    ts_to_pkts[ts] = []

                if 'tcps_sndtotal' not in vals['traffic']['server']:
                    ts_to_retrans[ts].append(0)
                    ts_to_pkts[ts].append(0)
                    continue

                retrns = 0
                if 'tcps_sndrexmitpack' in vals['traffic']['server']:
                    retrns = vals['traffic']['server']['tcps_sndrexmitpack']
                pkts = vals['traffic']['server']['tcps_sndtotal']

                ts_to_retrans[ts].append(retrns)
                ts_to_pkts[ts].append(pkts)
            
        to_plot = {'x': [], 'y': [], 'min_y': [], 'max_y': []}
        for ts, retrans in ts_to_retrans.items():
            percs = list(map(lambda x: (x[0] / x[1] * 100) if x[1] > 0 else 0, (zip(retrans, ts_to_pkts[ts]))))
            percs.append(percs[0])

            to_plot['x'].append(ts)
            to_plot['y'].append(statistics.mean(percs))
            to_plot['min_y'].append(min(percs))
            to_plot['max_y'].append(max(percs))

        plt.plot(to_plot['x'], to_plot['y'], linestyle=linestyle, fillstyle='none', color=color, marker=marker, label=label)

        for idx, x in enumerate(to_plot['x']):
            plt.errorbar(
                x, to_plot['y'][idx],
                yerr=[[to_plot['y'][idx] - to_plot['min_y'][idx]],
                    [to_plot['max_y'][idx] - to_plot['y'][idx]]],
                color=errorbar_color, elinewidth=1, capsize=1
            )

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    plot_retrans_line(os.path.join(results_path, "http_post"), 'HTTP', 'blue', "darkblue", "dashed", "s")
    plot_retrans_line(os.path.join(results_path, "allreduce"), 'All-Reduce', 'red', "darkred", "dashed", "^")

    plt.xlabel('Time [s]')
    plt.ylabel('TCP Retrans. [%]')
    ax = plt.gca()
    ax.set_xlim([0, 26])
    ax.set_ylim([0, 1.05])
    ax.set_xticks(range(0, 30, 5))
    ax.set_yticks(np.arange(0, 1.2, 0.2))
    plt.legend(loc="lower right", ncols=2, labelspacing=0.1, prop={'size': 8})
    plt.savefig(os.path.join(figures_path, f"trex.pdf"), format="pdf", bbox_inches='tight')


def plot_power_consumption_gbps_figure(results_path):
    global figures_path

    idle_file_path = os.path.join(results_path, "idle_watt.csv")
    nf_file_path = os.path.join(results_path, "nf1K_watt.csv")
    rdma_file_path = os.path.join(results_path, "rdma_watt.csv")

    data = {
        'idle': [],
        'nf': [],
        'rdma': []
    }
    with open(idle_file_path, "r") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        for row in reader:
            data['idle'].append(float(row['usage']))
    with open(nf_file_path, "r") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        for row in reader:
            data['nf'].append(float(row['usage']))
    with open(rdma_file_path, "r") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        for row in reader:
            data['rdma'].append(float(row['usage']))

    avg_nf_consumption = statistics.mean(data['nf'])
    avg_rnic_consumption = statistics.mean(data['rdma'])

    asic_base_consumption = 108
    additional_asic_consumption_per_gbps = 0.026
    cpu_base_consumption = statistics.mean(data['idle'])
    additional_rnic_consumption_per_gbps = (avg_rnic_consumption - cpu_base_consumption) / 100
    additional_nf_consumption_per_gbps = (avg_nf_consumption - avg_rnic_consumption) / 100
    fpga_base_consumption = 75
    pps_per_100gbps = 100_000_000_000 / (1500 * 8)
    hdr_size_bit = 64 * 8
    # Headers CPU load for 100Gbps
    cpu_load_per_100gbps = (pps_per_100gbps * hdr_size_bit) / 1_000_000_000

    def plot_queuemem_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            m = i + 1
            to_plot['x'].append(pps / 1_000_000)
            to_plot['y'].append(
                (asic_base_consumption + (additional_asic_consumption_per_gbps * ((m * 100) + (1 * cpu_load_per_100gbps))) +
                 cpu_base_consumption +
                 (
                         additional_rnic_consumption_per_gbps + additional_nf_consumption_per_gbps) * cpu_load_per_100gbps) / 1000
            )

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("Queue-Mem: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    def plot_ribosome_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            m = i + 1
            rdma_servers = round((100 * m) / 75)
            to_plot['x'].append(pps / 1_000_000)
            to_plot['y'].append(
                (asic_base_consumption + (additional_asic_consumption_per_gbps * (((m + rdma_servers) * 100) + (1 * cpu_load_per_100gbps))) +
                 (cpu_base_consumption +
                  (additional_rnic_consumption_per_gbps + additional_nf_consumption_per_gbps) * cpu_load_per_100gbps) +
                 (((cpu_base_consumption / 2) + (additional_rnic_consumption_per_gbps * 75)) * rdma_servers)) / 1000
            )

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("Ribosome: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    def plot_baseline_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            m = i + 1
            to_plot['x'].append(pps / 1000000)
            to_plot['y'].append(
                # m*100*2 because you need a NF port for each input port (m)
                (asic_base_consumption + (additional_asic_consumption_per_gbps * (m * 100 * 2)) +
                 ((cpu_base_consumption +
                   (additional_rnic_consumption_per_gbps + additional_nf_consumption_per_gbps) * 100) * m)) / 1000
            )
        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("Baseline: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    def plot_nicmem_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            m = i + 1
            to_plot['x'].append(pps / 1000000)
            to_plot['y'].append(
                # m*100*2 because you need a NF port for each input port (m)
                (asic_base_consumption + (additional_asic_consumption_per_gbps * (m * 100 * 2)) +
                 # CPU + we receive 100G on the NIC
                 ((cpu_base_consumption + (additional_rnic_consumption_per_gbps * 100) +
                   # We only receive headers on the NF
                   (additional_nf_consumption_per_gbps * cpu_load_per_100gbps)) * m)) / 1000
            )

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("nicmem: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    def plot_payloadpark_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        pp_cpu_load_per_100gbps = pps_per_100gbps * ((1500 - 160) * 8) / 1000000000
        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            m = i + 1
            nf_servers = round((pp_cpu_load_per_100gbps * m) / 100)
            to_plot['x'].append(pps / 1000000)
            to_plot['y'].append(
                (asic_base_consumption + (additional_asic_consumption_per_gbps * ((m * 100) + (nf_servers * pp_cpu_load_per_100gbps))) +
                 ((cpu_base_consumption +
                   (
                           additional_rnic_consumption_per_gbps + additional_nf_consumption_per_gbps) * pp_cpu_load_per_100gbps) * nf_servers)) / 1000
            )

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("Payload-Park: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    def plot_tiara_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        slow_path_load_per_100gbps = 10  # Only 10% of 100G is routed through the slow path
        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            m = i + 1
            to_plot['x'].append(pps / 1000000)
            to_plot['y'].append(
                # m input ports + m FPGA ports + 1 CPU socket
                (asic_base_consumption + (additional_asic_consumption_per_gbps * (((m + m) * 100) + (1 * slow_path_load_per_100gbps))) +
                 ((cpu_base_consumption +
                   (
                           additional_rnic_consumption_per_gbps + additional_nf_consumption_per_gbps) * slow_path_load_per_100gbps)) +
                 (fpga_base_consumption * m)) / 1000
            )

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("Tiara: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    def plot_asic_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            m = i + 1
            to_plot['x'].append(pps / 1_000_000)
            to_plot['y'].append(
                (asic_base_consumption + (additional_asic_consumption_per_gbps * (m * 100))) / 1000
            )

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("Ideal: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    plt.figure(figsize=(5.5, 1.8))

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    plot_baseline_power_line('gray', "Baseline", "dashed", "o")
    nicmem_watt = plot_nicmem_power_line('orange', "nicmem", "dotted", "^")
    payloadpark_watt = plot_payloadpark_power_line('red', "PayloadPark", "dashed", ".")
    ribosome_watt = plot_ribosome_power_line('blue', "Ribosome", "dashed", "v")
    queuemem_watt = plot_queuemem_power_line('green', "Queue-Mem", "dotted", "*")
    tiara_watt = plot_tiara_power_line('purple', "Tiara", "dotted", "D")
    plot_asic_power_line('yellowgreen', "Ideal", "dashed", ">")

    ax = plt.gca()
    ax.set_xlim([0, 100])
    plt.xticks(range(0, 110, 10), rotation=90)

    ax.set_yscale('log')
    plt.yticks([0.1, 1, 10])

    ax.annotate("", xy=(83.5, tiara_watt), xytext=(83.5, queuemem_watt),
                arrowprops=dict(arrowstyle="<->", color="purple"))
    plt.text(80, 0.6, f'{(tiara_watt / queuemem_watt):.1f}x', ha='center', va='bottom',
             fontdict={'color': 'purple', 'size': 8})

    ax.annotate("", xy=(91, ribosome_watt), xytext=(91, queuemem_watt),
                arrowprops=dict(arrowstyle="<->", color="royalblue"))
    plt.text(87.5, 0.6, f'{(ribosome_watt / queuemem_watt):.1f}x', ha='center', va='bottom',
             fontdict={'color': 'blue', 'size': 8})

    ax.annotate("", xy=(98.5, nicmem_watt), xytext=(98.5, queuemem_watt),
                arrowprops=dict(arrowstyle="<->", color="orange"))
    plt.text(95, 0.6, f'{(nicmem_watt / queuemem_watt):.1f}x', ha='center', va='bottom',
             fontdict={'color': 'orange', 'size': 8})

    plt.xlabel('Input Throughput [Mpps]')
    plt.ylabel('Power Usage [kW]')

    plt.legend(loc="upper center", bbox_to_anchor=(0.5, 1.33), ncol=4, labelspacing=0.2, prop={'size': 8})
    plt.savefig(os.path.join(figures_path, "pipeline_consumption.pdf"), format="pdf", bbox_inches='tight')

    def plot_power_consumption_bar(power_usage, color, label, linestyle):
        to_plot = {'x': [], 'y': [], 'dy': []}
        pps_per_100gbps = 100000000000 / (1500 * 8)
        pps = pps_per_100gbps * 100

        to_plot['x'].append(pps / 1000000)
        to_plot['y'].append(power_usage)

        bar = plt.bar(label, to_plot['y'], label=label, linestyle=linestyle, color=color)
        for rect in bar:
            height = rect.get_height()
            plt.text(rect.get_x() + rect.get_width() / 2.0, height,
                     f'{power_usage / queuemem_watt:.1f}x', ha='center', va='bottom',
                     fontdict={'color': color, 'size': 10})

    plt.clf()

    plt.figure(figsize=(4.5, 1.4))
    plt.grid(linestyle='--', linewidth=0.5)
    plot_power_consumption_bar(payloadpark_watt, 'red', "PayloadPark", "dashed")
    plot_power_consumption_bar(nicmem_watt, 'orange', "nicmem", "dashed")
    plot_power_consumption_bar(ribosome_watt, 'blue', "Ribosome", "dashed")
    plot_power_consumption_bar(queuemem_watt, 'green', "Queue-Mem", "dotted")

    ax = plt.gca()
    ax.set_axisbelow(True)

    plt.yticks([0, 1, 2, 3, 4, 5, 6])

    plt.ylabel('Power Usage\n[kW/Tbps]', fontdict={'linespacing': 1.7})
    plt.savefig(os.path.join(figures_path, "pipeline_consumption_bars.pdf"), format="pdf", bbox_inches='tight')


def plot_power_consumption_mpps_figure(results_path):
    global figures_path

    idle_file_path = os.path.join(results_path, "idle_watt.csv")
    nf1K_file_path = os.path.join(results_path, "nf1K_watt.csv")
    nf64B_file_path = os.path.join(results_path, "nf64B_watt.csv")
    rdma_file_path = os.path.join(results_path, "rdma_watt.csv")

    data = {
        'idle': [],
        'nf1K': [],
        'nf64B': [],
        'rdma': []
    }
    with open(idle_file_path, "r") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        for row in reader:
            data['idle'].append(float(row['usage']))
    with open(nf1K_file_path, "r") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        for row in reader:
            data['nf1K'].append(float(row['usage']))
    with open(nf64B_file_path, "r") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        for row in reader:
            data['nf64B'].append(float(row['usage']))
    with open(rdma_file_path, "r") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        for row in reader:
            data['rdma'].append(float(row['usage']))

    avg_nf1K_consumption = statistics.mean(data['nf1K'])
    avg_nf64B_consumption = statistics.mean(data['nf64B'])
    avg_rnic_consumption = statistics.mean(data['rdma'])

    asic_base_consumption = 108
    additional_asic_consumption_per_gbps = 0.026
    additional_asic_consumption_per_mpps = additional_asic_consumption_per_gbps / ((1_000_000_000 / (1500 * 8)) / 1_000_000)

    cpu_base_consumption = statistics.mean(data['idle'])
    additional_rnic_consumption_per_gbps = (avg_rnic_consumption - cpu_base_consumption) / 100
    additional_rnic_consumption_1K_per_mpps = additional_rnic_consumption_per_gbps / ((1_000_000_000 / (1500 * 8)) / 1_000_000)
    additional_rnic_consumption_64B_per_mpps = additional_rnic_consumption_per_gbps / ((1_000_000_000 / (64 * 8)) / 1_000_000)


    additional_nf1K_consumption_per_gbps = (avg_nf1K_consumption - avg_rnic_consumption) / 100
    additional_nf1K_consumption_per_mpps = additional_nf1K_consumption_per_gbps / ((1_000_000_000 / (1500 * 8)) / 1_000_000)

    additional_nf64B_consumption_per_gbps = (avg_nf64B_consumption - avg_rnic_consumption) / 100
    additional_nf64B_consumption_per_mpps = additional_nf64B_consumption_per_gbps / ((1_000_000_000 / (64 * 8)) / 1_000_000)

    fpga_base_consumption_per_gbps = 0.75
    fpga_base_consumption_per_mpps = fpga_base_consumption_per_gbps / ((1_000_000_000 / (1500 * 8)) / 1_000_000)

    pps_per_100gbps = 100_000_000_000 / (1500 * 8)
    mpps_per_100gbps = pps_per_100gbps / 1_000_000

    def plot_queuemem_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            input_mpps = pps / 1_000_000
            m = i + 1

            asic_power = asic_base_consumption + (additional_asic_consumption_per_mpps * ((m + 1) * mpps_per_100gbps))
            server_power = cpu_base_consumption + ((additional_rnic_consumption_64B_per_mpps + additional_nf64B_consumption_per_mpps) * input_mpps)
            queuemem_power = asic_power + server_power

            to_plot['x'].append(pps / 1_000_000)
            to_plot['y'].append(queuemem_power / 1000)

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("Queue-Mem: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    def plot_ribosome_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            input_mpps = pps / 1_000_000
            m = i + 1
            rdma_servers = round((100 * m) / 75)

            asic_power = asic_base_consumption + (additional_asic_consumption_per_mpps * ((m + rdma_servers + 1) * mpps_per_100gbps))
            server_power = cpu_base_consumption + ((additional_rnic_consumption_64B_per_mpps + additional_nf64B_consumption_per_mpps) * input_mpps)
            rdma_power = (cpu_base_consumption/2) + (additional_rnic_consumption_1K_per_mpps * (mpps_per_100gbps * 0.75))
            ribosome_power = asic_power + server_power + (rdma_power * rdma_servers)

            to_plot['x'].append(pps / 1_000_000)
            to_plot['y'].append(ribosome_power / 1000)

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("Ribosome: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    def plot_baseline_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            input_mpps = pps / 1_000_000
            m = i + 1

            # input_mpps*2 because you need a NF port for each input port (m)
            asic_power = asic_base_consumption + (additional_asic_consumption_per_mpps * (input_mpps * 2))
            server_power = cpu_base_consumption + (additional_rnic_consumption_1K_per_mpps + additional_nf1K_consumption_per_mpps) * mpps_per_100gbps
            baseline_power = asic_power + (server_power * m)

            to_plot['x'].append(pps / 1000000)
            to_plot['y'].append(baseline_power / 1000)

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("Baseline: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    def plot_nicmem_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        n_nic = 5

        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            input_mpps = pps / 1_000_000
            m = i + 1
            nf_servers = math.ceil(m / n_nic)
            pps_per_server = input_mpps / nf_servers

            # input_mpps*2 because you need a NF port for each input port (m)
            asic_power = asic_base_consumption + (additional_asic_consumption_per_mpps * (input_mpps * 2))
            server_power = cpu_base_consumption + (additional_rnic_consumption_1K_per_mpps * pps_per_server) + (additional_nf64B_consumption_per_mpps * pps_per_server)
            nicmem_power = asic_power + (server_power * nf_servers)

            to_plot['x'].append(pps / 1000000)
            to_plot['y'].append(nicmem_power / 1000)

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("nicmem: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    def plot_payloadpark_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        mpps_payloadpark = (100_000_000_000 / ((1500 - 160) * 8)) / 1_000_000

        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            input_mpps = pps / 1_000_000
            m = i + 1
            nf_servers = math.ceil((mpps_per_100gbps * m) / mpps_payloadpark)

            asic_power = asic_base_consumption + (additional_asic_consumption_per_mpps * (input_mpps * 2))
            server_power = cpu_base_consumption + (additional_rnic_consumption_1K_per_mpps + additional_nf1K_consumption_per_mpps) * mpps_payloadpark
            payloadpark_power = asic_power + (server_power * nf_servers)

            to_plot['x'].append(pps / 1000000)
            to_plot['y'].append(payloadpark_power / 1000)

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("Payload-Park: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    def plot_tiara_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        slow_path_load = 0.1  # Only 10% of 100G is routed through the slow path
        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            input_mpps = pps / 1_000_000
            m = i + 1

            # m input ports + m FPGA ports + 1 CPU socket    
            asic_power = asic_base_consumption + (additional_asic_consumption_per_mpps * (input_mpps + (input_mpps*(1-slow_path_load)) + (input_mpps * slow_path_load)))
            server_power = cpu_base_consumption + ((additional_rnic_consumption_1K_per_mpps + additional_nf1K_consumption_per_mpps) * (input_mpps * slow_path_load))
            fpga_power = fpga_base_consumption_per_mpps * (mpps_per_100gbps*(1-slow_path_load))
            tiara_power = asic_power + server_power + (fpga_power * m)

            to_plot['x'].append(pps / 1000000)
            to_plot['y'].append(tiara_power / 1000)

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("Tiara: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    def plot_asic_power_line(color, label, linestyle, marker):
        to_plot = {'x': [], 'y': [], 'dy': []}
        for i, pps in enumerate(map(lambda x: (x * pps_per_100gbps), range(1, 11))):
            input_mpps = pps / 1_000_000
            m = i + 1

            asic_power = asic_base_consumption + (additional_asic_consumption_per_mpps * input_mpps)

            to_plot['x'].append(pps / 1_000_000)
            to_plot['y'].append(asic_power / 1000)

        plt.plot(to_plot['x'], to_plot['y'], label=label, linestyle=linestyle, fillstyle='none', color=color,
                 marker=marker)

        print("Ideal: ", to_plot['y'][-1])

        return to_plot['y'][-1]

    plt.figure(figsize=(5.5, 1.8))

    plt.clf()
    plt.grid(linestyle='--', linewidth=0.5)
    plot_baseline_power_line('gray', "Baseline", "dashed", "o")
    nicmem_watt = plot_nicmem_power_line('orange', "nicmem", "dotted", "^")
    payloadpark_watt = plot_payloadpark_power_line('red', "PayloadPark", "dashed", ".")
    ribosome_watt = plot_ribosome_power_line('blue', "Ribosome", "dashed", "v")
    queuemem_watt = plot_queuemem_power_line('green', "Queue-Mem", "dotted", "*")
    tiara_watt = plot_tiara_power_line('purple', "Tiara", "dotted", "D")
    plot_asic_power_line('yellowgreen', "Ideal", "dashed", ">")

    ax = plt.gca()
    ax.set_xlim([0, 100])
    plt.xticks(range(0, 110, 10), rotation=90)

    ax.set_yscale('log')
    plt.yticks([0.1, 1, 10])

    ax.annotate("", xy=(83.5, nicmem_watt), xytext=(83.5, queuemem_watt),
                arrowprops=dict(arrowstyle="<->", color="orange"))
    plt.text(80, 0.6, f'{(nicmem_watt / queuemem_watt):.1f}x', ha='center', va='bottom',
             fontdict={'color': 'orange', 'size': 8})

    ax.annotate("", xy=(91, tiara_watt), xytext=(91, queuemem_watt),
                arrowprops=dict(arrowstyle="<->", color="purple"))
    plt.text(87.5, 0.6, f'{(tiara_watt / queuemem_watt):.1f}x', ha='center', va='bottom',
             fontdict={'color': 'purple', 'size': 8})

    ax.annotate("", xy=(98.5, ribosome_watt), xytext=(98.5, queuemem_watt),
                arrowprops=dict(arrowstyle="<->", color="blue"))
    plt.text(95, 0.6, f'{(ribosome_watt / queuemem_watt):.1f}x', ha='center', va='bottom',
             fontdict={'color': 'blue', 'size': 8})

    plt.xlabel('Input Throughput [Mpps]')
    plt.ylabel('Power Usage [kW]')

    plt.legend(loc="upper center", bbox_to_anchor=(0.5, 1.33), ncol=4, labelspacing=0.2, prop={'size': 8})
    plt.savefig(os.path.join(figures_path, "pipeline_consumption.pdf"), format="pdf", bbox_inches='tight')

    def plot_power_consumption_bar(power_usage, color, label, linestyle):
        to_plot = {'x': [], 'y': [], 'dy': []}
        pps_per_100gbps = 100000000000 / (1500 * 8)
        pps = pps_per_100gbps * 100

        to_plot['x'].append(pps / 1000000)
        to_plot['y'].append(power_usage)

        bar = plt.bar(label, to_plot['y'], label=label, linestyle=linestyle, color=color)
        for rect in bar:
            height = rect.get_height()
            plt.text(rect.get_x() + rect.get_width() / 2.0, height,
                     f'{power_usage / queuemem_watt:.1f}x', ha='center', va='bottom',
                     fontdict={'color': color, 'size': 10})

    plt.clf()

    plt.figure(figsize=(4.5, 1.4))
    plt.grid(linestyle='--', linewidth=0.5)
    plot_power_consumption_bar(payloadpark_watt, 'red', "PayloadPark\n(Switch SRAM)", "dashed")
    plot_power_consumption_bar(ribosome_watt, 'blue', "Ribosome\n(RDMA Server)", "dashed")
    plot_power_consumption_bar(nicmem_watt, 'orange', "nicmem\n(NIC Memory)", "dashed")
    plot_power_consumption_bar(queuemem_watt, 'green', "Queue-Mem\n(Switch Buffer)", "dotted")

    ax = plt.gca()
    ax.set_axisbelow(True)

    plt.yticks([0, 1, 2, 3, 4, 5, 6])
    ax.xaxis.set_tick_params(labelsize=7.5)

    plt.xlabel('Location', fontdict={'linespacing': 1.7})
    plt.ylabel('Power Usage\n[kW/Tbps]', fontdict={'linespacing': 1.7})
    plt.savefig(os.path.join(figures_path, "pipeline_consumption_bars.pdf"), format="pdf", bbox_inches='tight')

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: plot.py <results_path> <figures_path> <mcast>")
        exit(1)

    results_path = os.path.abspath(sys.argv[1])
    figures_path = os.path.abspath(sys.argv[2])
    mcast = sys.argv[3]

    print(f"Results Path: {results_path}")
    print(f"Figures Path: {figures_path}")
    print(f"Multicast: {mcast}")

    os.makedirs(figures_path, exist_ok=True)

    matplotlib.rc('font', size=10)
    matplotlib.rcParams['pdf.fonttype'] = 42
    matplotlib.rcParams['ps.fonttype'] = 42

    plot_power_consumption_mpps_figure(os.path.abspath("power_measurements_cx7"))

    plt.figure(figsize=(3, 1.3))
    plot_throughput_gbps_figure(
        os.path.join(results_path, "throughput"), "forwarder_throughput.pdf",
        ["Queue-Mem (Header-only)", "Baseline (Header+Payload)", "PayloadPark-like"]
    )

    plot_variable_throughput_figure(os.path.join(results_path, "incremental/{name}/" + mcast), 60, 10, 4, 5, 0, "incremental_throughput.pdf", True, True, True)
    plot_variable_throughput_figure(os.path.join(results_path, "incremental_drops/{name}/" + mcast), 60, 10, 4, 5, 0, "incremental_drops_throughput.pdf", False, False, True)

    plot_variable_throughput_figure(os.path.join(results_path, "random/{name}/" + mcast), 34, 4, 4, 5, 0, "random_throughput.pdf", True, True, False)
    plot_variable_throughput_figure(os.path.join(results_path, "random_drops/{name}/" + mcast), 34, 4, 4, 5, 0, "random_drops_throughput.pdf", False, False, False)
    
    plot_variable_throughput_figure(os.path.join(results_path, "peak/{name}/" + mcast), 34, 4, 4, 5, 0, "peak_throughput.pdf", True, True, False)
    plot_variable_throughput_figure(os.path.join(results_path, "peak_drops/{name}/" + mcast), 34, 4, 4, 5, 0, "peak_drops_throughput.pdf", False, False, False)
    
    plot_variable_throughput_figure(os.path.join(results_path, "caida/{name}/" + mcast), 6, 2, 1, 2, 4, "caida_throughput.pdf", True, True, False)
    plot_variable_throughput_figure(os.path.join(results_path, "caida_drops/{name}/" + mcast), 6, 2, 2, 0, 0, "caida_drops_throughput.pdf", False, False, False)
    
    plot_variable_throughput_figure(os.path.join(results_path, "mawi/{name}/" + mcast), 6, 2, 1, 2, 3, "mawi_throughput.pdf", True, True, True)
    plot_variable_throughput_figure(os.path.join(results_path, "mawi_drops/{name}/" + mcast), 6, 2, 2, 0, 0, "mawi_drops_throughput.pdf", False, False, False)
    
    plt.figure(figsize=(3, 1.3))
    plot_throughput_gbps_figure_nf(
        os.path.join(results_path, "throughput_nf"), "throughput_NF.pdf",
        ["FC+LB+RL", "LB+AES"]
    )

    plt.figure(figsize=(3, 1.3))
    plot_nf_drops_figure(os.path.join(results_path, "drops/" + mcast), 'NF Header Drops [%]', [0, 10, 20, 30, 40, 50], [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6], "drops_nf.pdf")

    plt.figure(figsize=(3, 1.3))
    plot_nf_drops_figure(os.path.join(results_path, "tail_drops/" + mcast), 'Batches w/ Drops [%]', range(0, 110, 20), [0.8, 1.0, 1.2, 1.4, 1.6], "tail_drops_nf.pdf")

    plot_bg_throughput_figure(os.path.join(results_path, "bg_traffic_iperf_tp/" + mcast), 6, 6, "bg_throughput.pdf")

    plt.figure(figsize=(3, 1.3))
    plot_bg_latency_figure(os.path.join(results_path, "bg_traffic_lat/" + mcast), 7)
 
    plt.figure(figsize=(3, 1.3))
    plot_reordering_slf_figure(os.path.join(results_path, "reordering"))

    plt.figure(figsize=(3, 1.3))
    plot_iperf_full_figure(os.path.join(results_path, "iperf_all"))

    plt.figure(figsize=(3, 1.3))
    plot_trex_figure(os.path.join(results_path, "trex"), 5)
