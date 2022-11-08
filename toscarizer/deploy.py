import requests
import time

try:
    # To avoid annoying InsecureRequestWarning messages in some Connectors
    import requests.packages
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    pass


def launch(tosca_file, im_url, auth_data, verify):
    headers = {"Authorization": auth_data}
    headers["Content-Type"] = "text/yaml"
    url = "%s/infrastructures" % im_url

    try:
        with open(tosca_file, 'r') as f:
            tosca_data = f.read()
        resp = requests.post(url, verify=verify, headers=headers, data=tosca_data)

        success = resp.status_code == 200
        return success, resp.text
    except Exception as ex:
        return False, str(ex)


def get_state(inf_id, auth_data, verify):
    headers = {"Authorization": auth_data}
    headers["Content-Type"] = "application/json"
    try:
        resp = requests.get("%s/state" % inf_id, verify=verify, headers=headers)
        success = resp.status_code == 200
        if success:
            return success, resp.json()["state"]["state"]
        else:
            return success, resp.text
    except Exception as ex:
        return False, str(ex)


def deploy(tosca_files, auth_data, im_url, verify, dag, delay=10, max_time=900):

    if dag:
        components_deployed = {}
        end = False
        cont = 0
        while not end and cont < max_time:
            for component, next_items in dag.adj.items():
                if component not in components_deployed:
                    # Check that all the next components has finished
                    all_ok = True
                    for next_comp in next_items:
                        if next_comp in components_deployed:
                            _, state = components_deployed[next_comp]
                        else:
                            state = 'pending'
                        if state != 'configured':
                            all_ok = False
                            if state not in ['pending', 'running']:
                                components_deployed[component] = ('Errors in previous deployments.', 'failed')

                    if all_ok:
                        tosca_file = [tf for tf in tosca_files if "%s.yaml" % component in tf][0]
                        if tosca_file:
                            print("Launching deployment for component %s" % component)
                            success = False
                            num = 1
                            while not success and num < 5:
                                success, inf_id = launch(tosca_file, im_url, auth_data, verify)
                                if not success:
                                    print("Error launching deployment for component %s. Waiting to retry." % component)
                                    time.sleep(num*10)
                                num += 1
                        else:
                            success = False
                            inf_id = "TOSCA file for component %s not found." % component
                        state = 'pending' if success else 'failed'
                        components_deployed[component] = (inf_id, state)
                else:
                    # Update deployment state
                    inf_id, state = components_deployed[component]
                    if state in ['pending', 'running']:
                        success, state = get_state(inf_id, auth_data, verify)
                        if success:
                            components_deployed[component] = inf_id, state

            end = True
            for component in dag.nodes():
                if component in components_deployed:
                    _, state = components_deployed[component]
                else:
                    state = 'pending'
                if state in ['pending', 'running']:
                    end = False
                    break

            if not end:
                time.sleep(delay)
                max_time += delay
    else:
        for file in tosca_files:
            success, inf_id = launch(file, im_url, auth_data, verify)
            components_deployed[file] = {}
            if success:
                components_deployed[file]["infId"] = inf_id
            else:
                components_deployed[file]["error"] = inf_id

    return components_deployed
