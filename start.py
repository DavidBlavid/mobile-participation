import sys
import subprocess
import threading

def launch_mobile_host(n_hosts):
    cmd = f"python -m src.client.controller {n_hosts}"
    subprocess.run(cmd, shell=True)

def launch_server(n_hosts):
    cmd = f"python -m src.server.server {n_hosts} -r"
    subprocess.run(cmd, shell=True)

def launch_monitor(n_hosts):
    cmd = f"python -m src.monitor.monitor {n_hosts}"
    subprocess.run(cmd, shell=True)

if __name__ == '__main__':
    # get the launch arguments
    arguments = sys.argv[1:]

    if len(arguments) < 1:
        print('Usage: python -m src.client.controller <number of hosts>')
        sys.exit(1)
    
    n_hosts = int(arguments[0])

    # collect threads
    threads = []

    thread_server = threading.Thread(target=launch_server, args=(n_hosts,))
    thread_server.start()
    threads.append(thread_server)

    thread_clients = threading.Thread(target=launch_mobile_host, args=(n_hosts,))
    thread_clients.start()
    threads.append(thread_clients)

    thread_monitor = threading.Thread(target=launch_monitor, args=(n_hosts,))
    thread_monitor.start()
    threads.append(thread_monitor)

    # wait for threads to finish
    for thread in threads:
        thread.join()