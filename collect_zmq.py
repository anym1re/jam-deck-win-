# collect_zmq.py
from modulegraph.modulegraph import ModuleGraph

def collect_zmq_dylibs(mf: ModuleGraph):
    m = mf.findNode('zmq')
    if m is None or m.filename is None:  # Check if zmq is even used
        return
    import zmq
    from pathlib import Path

    zmq_dir = Path(zmq.__file__).parent
    dylibs_dir = zmq_dir / ".dylibs"

    if dylibs_dir.exists():
        mf.import_hook('zmq', m, ['*'], dylibs_dir) # Key Change: import from dylibs_dir


if __name__ == '__main__':
    # Example Usage (for testing the helper script itself)
    mf = ModuleGraph()
    mf.run_script('music_server.py') # Replace 'your_main_script.py'
    collect_zmq_dylibs(mf)
    # You can print mf.graph here for debugging if needed.