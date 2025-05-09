import os
import subprocess
import time
import redis

class ClusterDeployer:
    def __init__(self):
        self.ports = [30001, 30002, 30003]
        self.processes = []

    def start_nodes(self):
        # Start Redis instances
        for port in self.ports:
            config = f"port {port}\ncluster-enabled yes\ncluster-config-file nodes-{port}.conf\n"
            with open(f"redis-{port}.conf", "w") as f:
                f.write(config)
            
            process = subprocess.Popen(
                ['redis-server', f'redis-{port}.conf'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append(process)
            time.sleep(0.5)

    def create_cluster(self):
        # Connect to each node
        nodes = [redis.Redis(port=port) for port in self.ports]
        
        # Reset cluster state
        for node in nodes:
            node.execute_command('CLUSTER RESET')

        # Make nodes meet each other
        for i, node in enumerate(nodes):
            for port in self.ports[i+1:]:
                node.execute_command('CLUSTER MEET', '127.0.0.1', port)
        time.sleep(1)

        # Assign slots
        slots_per_node = 16384 // len(self.ports)
        for i, node in enumerate(nodes):
            start = i * slots_per_node
            end = start + slots_per_node - 1 if i < len(self.ports)-1 else 16383
            for slot in range(start, end + 1):
                node.execute_command('CLUSTER ADDSLOTS', slot)

    def check_cluster(self):
        try:
            node = redis.Redis(port=self.ports[0])
            info = node.execute_command('CLUSTER INFO')
            if isinstance(info, bytes):
                info = info.decode('utf-8')
            return f"Cluster Info:\n{info}"
        except Exception as e:
            return f"Error checking cluster: {str(e)}"

    def cleanup(self):
        # Stop Redis processes
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(1)
            except:
                pass
        self.processes = []

        # Clean up files
        for port in self.ports:
            try:
                os.remove(f'redis-{port}.conf')
                os.remove(f'nodes-{port}.conf')
            except:
                pass
