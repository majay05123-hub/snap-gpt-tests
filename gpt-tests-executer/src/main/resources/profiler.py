#! /usr/bin/python3
"""
Simple process profiler.
"""
import sys
import os
import time
import argparse
import subprocess
import json
import psutil

# Directory name constants
__CSV_DIR__ = "csv"
__PLT_DIR__ = "plot"
__SUM_DIR__ = "stats"
__RPT_DIR__ = "performances"
# Conversion const
__MB__ = 2**20 # const for converting bytes to mega bytes
# PROCESS END STATUS
__END_STATUS__ = set([psutil.STATUS_STOPPED, psutil.STATUS_DEAD, psutil.STATUS_ZOMBIE])


# Simple class definition for statistics and paths
class ProcessStats:
    """
    Process profiling statistics class
    """
    def __init__(self):
        """Init ProcessStats."""
        self.stats = {
            'cpu_time' : [],
            'cpu_perc' : [],
            'memory'   : [],
            'threads'  : [],
            'io_write' : [],
            'io_read'  : [],
            'time'     : [],
        }
        self.__start___ = time.time()

    def update(self, process):
        """
        Updates process statistics.

        Parameters
        ----------
         - process: psutils.process to profile
        """
        io_counters = process.io_counters() # use system wide counters (not the process one)
        self.stats['io_read'].append(io_counters[0]) # read_bytes
        self.stats['io_write'].append(io_counters[1]) # write_bytes
        self.stats['memory'].append(int(round(process.memory_info().rss/__MB__))) # memory
        self.stats['cpu_perc'].append(int(process.cpu_percent())) # cpu usage
        self.stats['cpu_time'].append(process.cpu_times().user) # cpu time
        self.stats['threads'].append(process.num_threads()) # num threads
        # sampling time
        self.stats['time'].append(int(round(1000*(time.time() - self.__start___))))

    def summary(self):
        """
        compute statistics summary and print/save it as dict structure
        """
        tot = len(self.stats['time'])
        summary = {
            'duration': {
                'value' : int(round(self.stats['time'][-1] / 1000)),
                'unit'  : 's',
            },
            'memory': {
                'unit'    : 'Mb',
                'max'     : max(self.stats['memory']),
                'average' : int(round(sum(self.stats['memory']) / tot)),
            },
            'cpu_time': {
                'value': int(max(self.stats['cpu_time'])),
                'unit' : 's',
            },
            'cpu_usage': {
                'unit'    : '%',
                'max'     : max(self.stats['cpu_perc']),
                'average' : int(round(sum(self.stats['cpu_perc']) / tot)),
            },
            'io': {
                'write' : max(self.stats['io_write']),
                'read'  : max(self.stats['io_read']),
                'unit'  : '',
            },
            'threads': {
                'unit'    : '',
                'max'     : max(self.stats['threads']),
                'average' : sum(self.stats['threads']) / tot,
                'min'     : min(self.stats['threads']),
            },
        }
        return summary

    def csv(self):
        """
        generates the csv string for the stats
        """
        # Write out results (io or file)
        csv_string = f'#start time: {self.__start___}\n'
        csv_string += f'#cores:{psutil.cpu_count()}\n' # store number of CPU
        # columns label
        csv_string += '#time(ms), memory(Mb), CPU(s), CPU(%), Threads, Read IO (#), Write IO (#)\n'
        for i in range(len(self.stats['time'])): # iterate entries
            # create comma separated row
            csv_string += f"{self.stats['time'][i]},{self.stats['memory'][i]},"
            csv_string += f"{self.stats['cpu_time'][i]},{self.stats['cpu_perc'][i]},"
            csv_string += f"{self.stats['threads'][i]},{self.stats['io_read'][i]},"
            csv_string += f"{self.stats['io_write'][i]}\n"
        return csv_string

    def last_interval(self):
        """
        retrive the last delta intervals
        """
        if len(self.stats['time']) > 1:
            return self.stats['time'][-1] - self.stats['time'][-2]
        return self.stats['time'][0]


def __generate_report_table_row__(key, value, unit):
    """generates a row for the summary table of the html report."""
    return f"<tr><td><b>{key}:</b></td><td>{value:0.2f} {unit}</td></tr>"

class FileManager:
    """Report and output generation class"""
    def __init__(self, output_arg):
        self.__file_mode__ = output_arg is not None
        if self.__file_mode__:
            # init the path
            self.path_base = os.path.split(output_arg)[0]
            self.report_dir = os.path.join(self.path_base, __RPT_DIR__)
            self.path_csv = os.path.join(self.path_base, __RPT_DIR__, __CSV_DIR__)
            self.path_smm = os.path.join(self.path_base, __RPT_DIR__, __SUM_DIR__)
            self.path_plt = os.path.join(self.path_base, __RPT_DIR__, __PLT_DIR__)
            self.path_fname = os.path.split(output_arg)[1]
            # try to create CSV folder and Plot folder
            if not os.path.exists(self.report_dir):
                os.mkdir(self.report_dir)
            if not os.path.exists(self.path_csv):
                os.mkdir(self.path_csv)
            if not os.path.exists(self.path_plt):
                os.mkdir(self.path_plt)
            if not os.path.exists(self.path_smm):
                os.mkdir(self.path_smm)

    def csv(self, csv_string):
        """save or display the csv output"""
        if not self.__file_mode__: # print
            print(csv_string, end='')
        else: # save to file
            with open(os.path.join(self.path_csv, self.path_fname + ".csv"), 'w') as file:
                file.write(csv_string)

    def summary(self, smm_dict):
        """save or display summary structure"""
        summ_string = json.dumps(smm_dict) # generate json string
        if self.__file_mode__:
            with open(os.path.join(self.path_smm, self.path_fname + ".json"), 'w') as file:
                file.write(summ_string)
        else:
            print(summ_string)

    def plot(self, stats):
        """
        Plot process statistics using matplotlib.
        """
        # import required library
        import matplotlib.pyplot as plt

        # plot cpu usage
        plt.figure(figsize=(10, 7))
        plt.plot(stats.stats['time'], stats.stats['cpu_perc'])
        plt.xlabel("Elapsed time (ms)")
        plt.ylabel("CPU Usage (%)")
        plt.grid(alpha=0.5)
        plt.title("CPU Usage")
        if self.__file_mode__:
            plt.savefig(os.path.join(self.path_plt, self.path_fname+"_cpu_usage.png"))

        # plot memory usage
        plt.figure(figsize=(10, 7))
        plt.plot(stats.stats['time'], stats.stats['memory'])
        plt.xlabel("Elapsed time (ms)")
        plt.ylabel("Memory (Mb)")
        plt.grid(alpha=0.5)
        plt.title("Memory Usage")
        if self.__file_mode__:
            plt.savefig(os.path.join(self.path_plt, self.path_fname+"_memory_usage.png"))

        # plot io activity
        plt.figure(figsize=(10, 7))
        plt.plot(stats.stats['time'], stats.stats['io_read'], label='Read Count')
        plt.plot(stats.stats['time'], stats.stats['io_write'], label='Write Count')
        plt.legend()
        plt.xlabel("Elapsed time (ms)")
        plt.ylabel("Counter")
        plt.grid(alpha=0.5)
        plt.title("Disk IO Activity")
        if self.__file_mode__:
            plt.savefig(os.path.join(self.path_plt, self.path_fname+"_IO_usage.png"))

        # show results if no output is defined
        if not self.__file_mode__:
            plt.show()


def __split_command_args__(command):
    """
    splits command in list of arguments.
    """
    args = []
    status = True
    token = ""
    for char in command:
        if char == " ":
            if status:
                if token:
                    args.append(token)
                token = ""
            else:
                token += " "
        elif char == '"':
            status = not status
            if status:
                if token:
                    args.append(token)
                token = ""
        else:
            token += char
    if token:
        args.append(token)
    return args


def __arguments__():
    """
    parse arguments passed by the command line
    """
    # setup arg parser
    parser = argparse.ArgumentParser()

    parser.add_argument('command',
                        help="command to profile")
    parser.add_argument('--frequence',
                        default=200,
                        help="sampling period in ms")
    parser.add_argument('-o',
                        default=None,
                        help="save results to file")
    parser.add_argument('-w',
                        choices=[True, False],
                        default=False,
                        help="wait time before starting profiling [default=True]")
    parser.add_argument('-c',
                        default=False,
                        help="profile children flag [default=True]",
                        choices=[True, False])
    parser.add_argument('--plot',
                        default=True,
                        help="plot perforamnces (save if save file setted)",
                        choices=[True, False])
    parser.add_argument('--report',
                        default=None,
                        help="HTML report template")

    # parse arguments
    return parser.parse_args()


def main():
    """
    main entry point of the profiler
    """
    # parse_arguments
    args = __arguments__()
    # split command in sub parts
    command = __split_command_args__(args.command)

    sampling_time = args.frequence/1000.0 # convert period from ms to s

    # execute the command and retrive the PID
    proc = subprocess.Popen(command)
    pid = proc.pid

    # wait some time according to arguments
    if args.w:
        time.sleep(2)

    # check if porcessing (still) exists
    if not psutil.pid_exists(pid):
        print("Process not found...")
        sys.exit(-1)

    # get process
    process = psutil.Process(pid)
    if args.c: # if profiling on children process try to get children process
        chld = process.children()
        process = process if chld else chld[0]

    # initilize results variables
    pid = process.pid
    p_stats = ProcessStats()
    while psutil.pid_exists(pid) and process.status() not in __END_STATUS__:
        # while process is running
        p_stats.update(process) # update stats
        time.sleep(sampling_time) # wait for next sampling

    # Output
    output = args.o
    # initialize path structure and make output directories
    perf_fm = FileManager(output)
    # generate csv string and display/store it
    perf_fm.csv(p_stats.csv())
    # compute and save/display statistic summary (max, average...)
    summary = p_stats.summary()
    # display/store summary
    perf_fm.summary(summary)

    # plot results if needed
    # NOTE: only import matplotlib library here to avoid including it and limiting the functionality
    # when not needed
    if args.plot:
        perf_fm.plot(p_stats)

if __name__ == "__main__":
    main()