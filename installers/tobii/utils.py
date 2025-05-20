import os

# Check whether keepalive exists or not
def ka_exists(base_path):
    return os.path.exists(f"{base_path}/tmp/keepalive.td")

