import unittest
import sys
import os
import yaml
from click.testing import CliRunner
from mock import patch, MagicMock


sys.path.append("..")
sys.path.append(".")

from toscarizer.bin.toscarizer_cli import toscarizer_cli

tests_path = os.path.dirname(os.path.abspath(__file__))


class TestToscarizer(unittest.TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)

    def test_00_docker(self):
        files = ['aisprint/designs/blurry-faces-onnx/base/Dockerfile',
                 'aisprint/designs/blurry-faces-onnx/partition1_1/Dockerfile',
                 'aisprint/designs/blurry-faces-onnx/partition1_2/Dockerfile',
                 'aisprint/designs/mask-detector/base/Dockerfile',
                 'aisprint/designs/blurry-faces-onnx/base/script.sh',
                 'aisprint/designs/blurry-faces-onnx/partition1_1/script.sh',
                 'aisprint/designs/blurry-faces-onnx/partition1_2/script.sh',
                 'aisprint/designs/mask-detector/base/script.sh'
        ]
        application_dir = os.path.join(tests_path, "../app_demo")

        runner = CliRunner()
        result = runner.invoke(toscarizer_cli, ['docker', "--dry-run", '--application_dir', application_dir,
                                                "--registry", "docker.io", "--registry_folder",
                                                "/micafer", "--username", "user", "--password", "pass"])

        self.assertEqual(result.exit_code, 0)
        for fname in files:
            self.assertTrue(os.path.isfile(os.path.join(application_dir, fname)))
            os.unlink(os.path.join(application_dir, fname))

        with open(os.path.join(application_dir, 'aisprint/designs/containers.yaml'), 'r') as f:
            containers = yaml.safe_load(f)
        expected = {
            'components': {
                'blurry-faces-onnx': {
                    'docker_images': [
                        'docker.io/micafer/blurry-faces-onnx_base_arm64:latest',
                        'docker.io/micafer/blurry-faces-onnx_base_amd64:latest',
                        'docker.io/micafer/blurry-faces-onnx_partition1_2_amd64:latest',
                        'docker.io/micafer/blurry-faces-onnx_partition1_1_arm64:latest'
                    ]
                },
                'mask-detector': {
                    'docker_images': [
                        'docker.io/micafer/mask-detector_base_amd64:latest'
                    ]
                }
            }
        }
        self.assertEqual(containers, expected)

    @patch('toscarizer.im_tosca.get_random_string')
    def test_10_tosca(self, random_string):
        random_string.return_value = "fixed"
        application_dir = os.path.join(tests_path, "../app_demo")
        # Test base case
        runner = CliRunner()
        result = runner.invoke(toscarizer_cli, ['tosca', '--application_dir', application_dir, "--base"])
        self.assertEqual(result.exit_code, 0)

        c1 = open(os.path.join(application_dir, "aisprint/deployments/base/im/blurry-faces-onnx.yaml")).read()
        c2 = open(os.path.join(application_dir, "aisprint/deployments/base/im/mask-detector.yaml")).read()
        c1_exp = open(os.path.join(tests_path, "blurry-faces-onnx.yaml")).read()
        c2_exp = open(os.path.join(tests_path, "mask-detector.yaml")).read()

        self.assertEqual(c1, c1_exp)
        self.assertEqual(c2, c2_exp)

        # Test optimal case
        result = runner.invoke(toscarizer_cli, ['tosca', '--application_dir', application_dir, "--optimal"])
        self.assertEqual(result.exit_code, 0)

        os.unlink(os.path.join(application_dir, 'aisprint/designs/containers.yaml'))
        c1 = open(os.path.join(application_dir, "aisprint/deployments/base/im/blurry-faces-onnx.yaml")).read()
        c2 = open(os.path.join(application_dir, "aisprint/deployments/base/im/mask-detector.yaml")).read()
        c1_exp = open(os.path.join(tests_path, "blurry-faces-onnx.yaml")).read()
        c2_exp = open(os.path.join(tests_path, "mask-detector.yaml")).read()

        self.assertEqual(c1, c1_exp)
        self.assertEqual(c2, c2_exp)

    def test_20_fdl(self):
        application_dir = os.path.join(tests_path, "../app_demo")
        # Test base case
        runner = CliRunner()
        result = runner.invoke(toscarizer_cli, ['fdl', '--application_dir', application_dir, "--base"])
        self.assertEqual(result.exit_code, 0)

        fdl = open(os.path.join(application_dir, "aisprint/deployments/base/oscar/fdl.yaml")).read()
        os.unlink(os.path.join(application_dir, "aisprint/deployments/base/oscar/fdl.yaml"))
        fdl_exp = open(os.path.join(tests_path, "fdl.yaml")).read()

        self.assertEqual(fdl, fdl_exp)

        # Test optimal case
        result = runner.invoke(toscarizer_cli, ['fdl', '--application_dir', application_dir, "--optimal"])
        self.assertEqual(result.exit_code, 0)

        fdl = open(os.path.join(application_dir, "aisprint/deployments/optimal_deployment/oscar/fdl.yaml")).read()
        os.unlink(os.path.join(application_dir, "aisprint/deployments/optimal_deployment/oscar/fdl.yaml"))
        fdl_exp = open(os.path.join(tests_path, "fdl.yaml")).read()

        self.assertEqual(fdl, fdl_exp)

    @patch('requests.get')
    @patch('requests.post')
    @patch('time.sleep')
    def test_30_deploy(self, sleep, post, get):
        create_im = MagicMock()
        create_im.status_code = 200
        create_im.text = "https://im/inf_id1"
        create_im2 = MagicMock()
        create_im2.status_code = 200
        create_im2.text = "https://im/inf_id2"
        post.side_effect = [create_im, create_im2 ]
        get_state = MagicMock()
        get_state.status_code = 200
        get_state.json.return_value = {"state": {"state": "configured"}}
        get.return_value = get_state

        application_dir = os.path.join(tests_path, "../app_demo")
        runner = CliRunner()
        result = runner.invoke(toscarizer_cli, ['deploy', '--application_dir', application_dir, "--base",])
        self.assertEqual(result.exit_code, 0)

        os.unlink(os.path.join(application_dir, "aisprint/deployments/base/im/blurry-faces-onnx.yaml"))
        os.unlink(os.path.join(application_dir, "aisprint/deployments/base/im/mask-detector.yaml"))

        infras = open(os.path.join(application_dir, "aisprint/deployments/base/im/infras.yaml")).read()
        self.assertEqual(infras, ("blurry-faces-onnx:\n- https://im/inf_id2\n- configured\n"
                                  "mask-detector:\n- https://im/inf_id1\n- configured\n"))

        self.assertIn("COMPONENT_NAME: mask-detector", post.call_args_list[0][1]["data"])
        self.assertIn("COMPONENT_NAME: blurry-faces-onnx", post.call_args_list[1][1]["data"])

    @patch('requests.delete')
    def test_40_delete(self, delete):
        delete_resp = MagicMock()
        delete_resp.status_code = 200
        delete_resp.text = ""
        delete.return_value = delete_resp

        application_dir = os.path.join(tests_path, "../app_demo")
        runner = CliRunner()
        result = runner.invoke(toscarizer_cli, ['delete', '--application_dir', application_dir, "--base",])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(delete.call_args_list[0][0][0], 'https://im/inf_id2')
        self.assertEqual(delete.call_args_list[1][0][0], 'https://im/inf_id1')


if __name__ == "__main__":
    unittest.main()
