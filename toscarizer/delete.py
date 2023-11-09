# Copyright (C) GRyCAP - I3M - UPV
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import requests

try:
    # To avoid annoying InsecureRequestWarning messages
    import requests.packages
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    pass


def destroy(im_infras, auth_data, verify):
    headers = {"Authorization": auth_data}
    all_ok = True
    for component, value in im_infras.items():
        inf_id = value[0]
        if inf_id.startswith("http"):
            print("Deleting infrastructure for component: %s ..." % component)
            try:
                resp = requests.delete(inf_id, headers=headers, verify=verify)
                success = resp.status_code == 200
                msg = resp.text
            except Exception as ex:
                success = False
                msg = str(ex)

            if success:
                print("Infrastructure successfully deleted.")
            else:
                print("Error deleting infrastructure: %s." % msg)
                all_ok = False

    return all_ok
