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
        self.maxDiff = None
        unittest.TestCase.__init__(self, *args)

    def test_00_docker(self):
        files = ['aisprint/designs/blurry-faces-onnx/base/Dockerfile',
                 'aisprint/designs/blurry-faces-onnx/partition1_1/Dockerfile',
                 'aisprint/designs/blurry-faces-onnx/partition1_2/Dockerfile',
                 'aisprint/designs/mask-detector/base/Dockerfile',
                 'aisprint/designs/mask-detector/base/Dockerfile.aws',
                 'aisprint/designs/blurry-faces-onnx/base/script.sh',
                 'aisprint/designs/blurry-faces-onnx/partition1_1/script.sh',
                 'aisprint/designs/blurry-faces-onnx/partition1_2/script.sh',
                 'aisprint/designs/mask-detector/base/script.sh']
        application_dir = os.path.join(tests_path, "../app_test")

        runner = CliRunner()
        result = runner.invoke(toscarizer_cli, ['docker', "--dry-run", '--application_dir', application_dir,
                                                "--registry", "docker.io", "--registry_folder", "/micafer",
                                                "--ecr", "000000000000.dkr.ecr.us-east-1.amazonaws.com/repo"])

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
                        'docker.io/micafer/mask-detector_base_amd64:latest',
                        '000000000000.dkr.ecr.us-east-1.amazonaws.com/repo:mask-detector_base_amd64'
                    ]
                }
            }
        }
        self.assertEqual(containers, expected)

    @patch('toscarizer.im_tosca.get_random_string')
    def test_05_tosca(self, random_string):
        random_string.side_effect = ["fixed1", "fixed2", "fixed3", "fixed4", "fixed1", "fixed6", "fixed7", "fixed4",
                                     "fixed9", "fixed10", "fixed11", "fixed12", "fixed13", "fixed14", "fixed15",
                                     "fixed16"]
        application_dir = os.path.join(tests_path, "../app_test")

        # Test base elastic case
        runner = CliRunner()
        result = runner.invoke(toscarizer_cli, ['tosca', '--application_dir', application_dir, '--base'])
        self.assertEqual(result.exit_code, 0)

        c1 = open(os.path.join(application_dir, "aisprint/deployments/base/im/blurry-faces-onnx.yaml")).read()
        c2 = open(os.path.join(application_dir, "aisprint/deployments/base/im/mask-detector.yaml")).read()
        c1_exp = open(os.path.join(tests_path, "blurry-faces-onnx-aws.yaml")).read()
        c2_exp = open(os.path.join(tests_path, "mask-detector-aws.yaml")).read()

        os.unlink(os.path.join(application_dir,
                               "aisprint/deployments/base/im/blurry-faces-onnx.yaml"))
        os.unlink(os.path.join(application_dir,
                               "aisprint/deployments/base/im/mask-detector.yaml"))

        self.assertEqual(c1, c1_exp)
        self.assertEqual(c2, c2_exp)

        # Test optimal case
        result = runner.invoke(toscarizer_cli, ['tosca', '--application_dir', application_dir, '--optimal',
                                                '--influxdb_token', 'influx_token'])
        self.assertEqual(result.exit_code, 0)

        c1 = open(os.path.join(application_dir,
                               "aisprint/deployments/optimal_deployment/im/blurry-faces-onnx_partition1_1.yaml")).read()
        c2 = open(os.path.join(application_dir,
                               "aisprint/deployments/optimal_deployment/im/blurry-faces-onnx_partition1_2.yaml")).read()
        c3 = open(os.path.join(application_dir,
                               "aisprint/deployments/optimal_deployment/im/mask-detector.yaml")).read()
        c1_exp = open(os.path.join(tests_path, "blurry-faces-onnx_partition1_1-aws.yaml")).read()
        c2_exp = open(os.path.join(tests_path, "blurry-faces-onnx_partition1_2-aws.yaml")).read()
        c3_exp = open(os.path.join(tests_path, "mask-detector-optimal-aws.yaml")).read()

        os.unlink(os.path.join(application_dir,
                               "aisprint/deployments/optimal_deployment/im/blurry-faces-onnx_partition1_1.yaml"))
        os.unlink(os.path.join(application_dir,
                               "aisprint/deployments/optimal_deployment/im/blurry-faces-onnx_partition1_2.yaml"))
        os.unlink(os.path.join(application_dir,
                               "aisprint/deployments/optimal_deployment/im/mask-detector.yaml"))
        os.unlink(os.path.join(application_dir, 'aisprint/designs/containers.yaml'))

        self.assertEqual(c1, c1_exp)
        self.assertEqual(c2, c2_exp)
        self.assertEqual(c3, c3_exp)

    def test_10_docker(self):
        files = ['aisprint/designs/blurry-faces-onnx/base/Dockerfile',
                 'aisprint/designs/blurry-faces-onnx/partition1_1/Dockerfile',
                 'aisprint/designs/blurry-faces-onnx/partition1_2/Dockerfile',
                 'aisprint/designs/mask-detector/base/Dockerfile',
                 'aisprint/designs/blurry-faces-onnx/base/script.sh',
                 'aisprint/designs/blurry-faces-onnx/partition1_1/script.sh',
                 'aisprint/designs/blurry-faces-onnx/partition1_2/script.sh',
                 'aisprint/designs/mask-detector/base/script.sh']
        application_dir = os.path.join(tests_path, "../app_demo")

        runner = CliRunner()
        result = runner.invoke(toscarizer_cli, ['docker', "--dry-run", '--application_dir', application_dir,
                                                "--registry", "docker.io", "--registry_folder", "/micafer"])

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
    def test_15_tosca(self, random_string):
        random_string.side_effect = ["fixed1", "fixed2", "fixed3", "fixed4", "fixed5", "fixed6", "fixed1", "fixed4",
                                     "fixed3", "fixed10", "fixed11", "fixed6", "fixed13", "fixed14", "fixed15",
                                     "fixed16", "fixed17", "fixed18", "fixed19", "fixed20", "fixed21", "fixed22",
                                     "fixed23"]
        application_dir = os.path.join(tests_path, "../app_demo")

        # Test base elastic case
        runner = CliRunner()
        result = runner.invoke(toscarizer_cli, ['tosca', '--application_dir', application_dir,
                                                '--base', '--elastic', '5'])
        self.assertEqual(result.exit_code, 0)

        c1 = open(os.path.join(application_dir, "aisprint/deployments/base/im/blurry-faces-onnx.yaml")).read()
        c2 = open(os.path.join(application_dir, "aisprint/deployments/base/im/mask-detector.yaml")).read()
        c1_exp = open(os.path.join(tests_path, "blurry-faces-onnx.yaml")).read()
        c2_exp = open(os.path.join(tests_path, "mask-detector_elastic.yaml")).read()

        self.assertEqual(c1, c1_exp)
        self.assertEqual(c2, c2_exp)

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
        c1 = open(os.path.join(application_dir,
                               "aisprint/deployments/optimal_deployment/im/blurry-faces-onnx_partition1_1.yaml")).read()
        c2 = open(os.path.join(application_dir,
                               "aisprint/deployments/optimal_deployment/im/blurry-faces-onnx_partition1_2.yaml")).read()
        c3 = open(os.path.join(application_dir,
                               "aisprint/deployments/optimal_deployment/im/mask-detector.yaml")).read()
        c1_exp = open(os.path.join(tests_path, "blurry-faces-onnx_partition1_1.yaml")).read()
        c2_exp = open(os.path.join(tests_path, "blurry-faces-onnx_partition1_2.yaml")).read()
        c3_exp = open(os.path.join(tests_path, "mask-detector-optimal.yaml")).read()

        self.assertEqual(c1, c1_exp)
        self.assertEqual(c2, c2_exp)
        self.assertEqual(c3, c3_exp)

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
        fdl_exp = open(os.path.join(tests_path, "fdl_optimal.yaml")).read()

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
        create_im3 = MagicMock()
        create_im3.status_code = 200
        create_im3.text = "https://im/inf_id3"
        create_im4 = MagicMock()
        create_im4.status_code = 200
        create_im4.text = "https://im/inf_id4"
        create_im5 = MagicMock()
        create_im5.status_code = 200
        create_im5.text = "https://im/inf_id5"
        post.side_effect = [create_im, create_im2, create_im3, create_im4, create_im5]
        get_state_conf = MagicMock()
        get_state_conf.status_code = 200
        get_state_conf.json.return_value = {"state": {"state": "configured"}}
        get_state_unconf = MagicMock()
        get_state_unconf.status_code = 200
        get_state_unconf.json.return_value = {"state": {"state": "unconfigured"}}
        get_contmsg = MagicMock()
        get_contmsg.status_code = 200
        get_contmsg.text = 'CONTMSG'
        get.side_effect = [get_state_conf, get_state_conf, get_state_conf, get_state_conf, get_state_unconf, get_contmsg]

        application_dir = os.path.join(tests_path, "../app_demo")
        runner = CliRunner()
        result = runner.invoke(toscarizer_cli, ['deploy', '--application_dir', application_dir, "--base"])
        self.assertEqual(result.exit_code, 0)

        os.unlink(os.path.join(application_dir, "aisprint/deployments/base/im/blurry-faces-onnx.yaml"))
        os.unlink(os.path.join(application_dir, "aisprint/deployments/base/im/mask-detector.yaml"))

        infras = open(os.path.join(application_dir, "aisprint/deployments/base/im/infras.yaml")).read()
        self.assertEqual(infras, ("blurry-faces-onnx:\n- https://im/inf_id2\n- configured\n- ''\n"
                                  "mask-detector:\n- https://im/inf_id1\n- configured\n- ''\n"))

        self.assertIn("COMPONENT_NAME: mask-detector", post.call_args_list[0][1]["data"])
        self.assertIn("COMPONENT_NAME: blurry-faces-onnx", post.call_args_list[1][1]["data"])

        application_dir = os.path.join(tests_path, "../app_demo")
        runner = CliRunner()
        result = runner.invoke(toscarizer_cli, ['deploy', '--application_dir', application_dir, "--optimal"])
        self.assertEqual(result.exit_code, 0)

        os.unlink(os.path.join(application_dir,
                               "aisprint/deployments/optimal_deployment/im/blurry-faces-onnx_partition1_1.yaml"))
        os.unlink(os.path.join(application_dir,
                               "aisprint/deployments/optimal_deployment/im/blurry-faces-onnx_partition1_2.yaml"))
        os.unlink(os.path.join(application_dir,
                               "aisprint/deployments/optimal_deployment/im/mask-detector.yaml"))

        infras = open(os.path.join(application_dir, "aisprint/deployments/optimal_deployment/im/infras.yaml")).read()
        self.assertEqual(infras, ("blurry-faces-onnx_partition1_1:\n- https://im/inf_id5\n- unconfigured\n- CONTMSG\n"
                                  "blurry-faces-onnx_partition1_2:\n- https://im/inf_id4\n- configured\n- ''\n"
                                  "mask-detector:\n- https://im/inf_id3\n- configured\n- ''\n"))

        self.assertIn("COMPONENT_NAME: mask-detector", post.call_args_list[2][1]["data"])
        self.assertIn("COMPONENT_NAME: blurry-faces-onnx_partition1_2", post.call_args_list[3][1]["data"])
        self.assertIn("COMPONENT_NAME: blurry-faces-onnx_partition1_1", post.call_args_list[4][1]["data"])

    @patch('requests.get')
    @patch('builtins.print')
    def test_40_outputs(self, mock_print, get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"outputs": {"out1": "value1"}}
        get.return_value = resp

        application_dir = os.path.join(tests_path, "../app_demo")
        runner = CliRunner()

        result = runner.invoke(toscarizer_cli, ['outputs', '--application_dir', application_dir, "--base"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(get.call_args_list[0][0][0], 'https://im/inf_id2/outputs')
        self.assertEqual(get.call_args_list[1][0][0], 'https://im/inf_id1/outputs')
        self.assertEqual(mock_print.call_args_list[0][0][0], ('blurry-faces-onnx:\n'
                                                              '  out1: value1\n'
                                                              'mask-detector:\n'
                                                              '  out1: value1\n'))

        result = runner.invoke(toscarizer_cli, ['outputs', '--application_dir', application_dir, "--optimal"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(get.call_args_list[2][0][0], 'https://im/inf_id5/outputs')
        self.assertEqual(get.call_args_list[3][0][0], 'https://im/inf_id4/outputs')
        self.assertEqual(get.call_args_list[4][0][0], 'https://im/inf_id3/outputs')
        self.assertEqual(mock_print.call_args_list[1][0][0], ('blurry-faces-onnx_partition1_1:\n'
                                                              '  out1: value1\n'
                                                              'blurry-faces-onnx_partition1_2:\n'
                                                              '  out1: value1\n'
                                                              'mask-detector:\n'
                                                              '  out1: value1\n'))

    @patch('requests.delete')
    def test_50_delete(self, delete):
        delete_resp = MagicMock()
        delete_resp.status_code = 200
        delete_resp.text = ""
        delete.return_value = delete_resp

        application_dir = os.path.join(tests_path, "../app_demo")
        runner = CliRunner()
        result = runner.invoke(toscarizer_cli, ['delete', '--application_dir', application_dir, "--base"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(delete.call_args_list[0][0][0], 'https://im/inf_id2')
        self.assertEqual(delete.call_args_list[1][0][0], 'https://im/inf_id1')

        result = runner.invoke(toscarizer_cli, ['delete', '--application_dir', application_dir, "--optimal"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(delete.call_args_list[2][0][0], 'https://im/inf_id5')
        self.assertEqual(delete.call_args_list[3][0][0], 'https://im/inf_id4')
        self.assertEqual(delete.call_args_list[4][0][0], 'https://im/inf_id3')


if __name__ == "__main__":
    unittest.main()
