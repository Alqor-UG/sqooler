import json

from utils import drpbx
from singlequdit.spooler_singlequdit import sq_spooler
# singlequdit
requested_backend = "singlequdit"

# the path and name
dbx_path = "/Backend_files/Config/" + requested_backend + "/config.json"

# the content
backend_config_dict = sq_spooler.get_configuration()

result_binary = json.dumps(backend_config_dict).encode("utf-8")
# upload the content
drpbx.upload(result_binary, dbx_path)