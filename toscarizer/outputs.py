import requests

try:
    # To avoid annoying InsecureRequestWarning messages
    import requests.packages
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    pass


def get_outputs(im_infras, auth_data, verify):
    headers = {"Authorization": auth_data, "Accept": "application/json"}
    res = {}
    for component, value in im_infras.items():
        inf_id = value[0]
        if inf_id.startswith("http"):
            try:
                resp = requests.get("%s/outputs" % inf_id, headers=headers, verify=verify)
                res[component] = resp.json()["outputs"]
            except Exception as ex:
                res[component] = "Error: %s" % str(ex)

    return res
