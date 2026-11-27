"""pack.py SCRIPT [data.json] [module.py ...] > main.py
Kaggle script kernels upload one file only: the data and the helper modules ride inside it and are unpacked at start."""
import base64, os, sys
script, rest = sys.argv[1], sys.argv[2:]
files = {os.path.basename(f): base64.b64encode(open(f, "rb").read()).decode() for f in rest}
print("import base64, os, sys\nos.makedirs('/kaggle/working/src', exist_ok=True)")
print(f"FILES = {files!r}")
print("for n, b in FILES.items():\n    open('/kaggle/working/src/' + n, 'wb').write(base64.b64decode(b))")
print("sys.path.insert(0, '/kaggle/working/src')")
print(open(os.path.join(os.path.dirname(__file__), script), encoding="utf-8").read())
