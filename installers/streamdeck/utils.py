import os

# Check whether keepalive exists or not
def ka_exists():
    return os.path.exists("tmp/keepalive.td")

