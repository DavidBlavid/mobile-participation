import subprocess
import threading
import sys

def launch_mobile_host(env_number):
    cmd = f"python -m src.client.host -e {env_number}"
    subprocess.run(cmd, shell=True)

def launch_multiple_hosts(n):
    threads = []
    for i in range(n):
        thread = threading.Thread(target=launch_mobile_host, args=(i+1,))
        print(f"Launched host {i+1}")
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    # get the launch arguments
    arguments = sys.argv[1:]

    if len(arguments) < 1:
        print('Usage: python -m src.client.controller <number of hosts>')
        sys.exit(1)
    
    n_hosts = int(arguments[0])
    
    launch_multiple_hosts(n_hosts)