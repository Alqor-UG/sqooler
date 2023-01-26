import json

from utils import drpbx
from singlequdit.spooler_singlequdit import sq_spooler
from multiqudit.spooler_multiqudit import mq_spooler
from fermions.spooler_fermions import f_spooler

backends = {
    "singlequdit": sq_spooler,
    "multiqudit": mq_spooler,
    "fermions": f_spooler
}

for requested_backend, spooler in backends.items():
    # the path and name
    dbx_path = "/Backend_files/Config/" + requested_backend + "/config.json"

    # the content
    backend_config_dict = spooler.get_configuration()

    result_binary = json.dumps(backend_config_dict).encode("utf-8")
    # upload the content
    drpbx.upload(result_binary, dbx_path)