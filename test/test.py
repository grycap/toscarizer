import unittest
import sys
import os
import yaml
from click.testing import CliRunner

sys.path.append("..")
sys.path.append(".")

from toscarizer.bin.toscarizer_cli import toscarizer_cli

tests_path = os.path.dirname(os.path.abspath(__file__))


class TestToscarizer(unittest.TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)

    def test_docker(self):
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
        try:
            for fname in files:
                os.unlink(os.path.join(application_dir, fname))
        except Exception:
            pass
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
        os.unlink(os.path.join(application_dir, 'aisprint/designs/containers.yaml'))
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


if __name__ == "__main__":
    unittest.main()
