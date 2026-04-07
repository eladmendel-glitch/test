import unittest

from slack_build_handler import EXPECTED_FORMAT, handle_slack_command, parse_build_command


class SlackBuildHandlerTests(unittest.TestCase):
    def test_ignores_non_build_messages(self) -> None:
        request, error = parse_build_command("hello team")
        self.assertIsNone(request)
        self.assertIsNone(error)

    def test_rejects_unknown_job(self) -> None:
        request, error = parse_build_command("build deploy-db")
        self.assertIsNone(request)
        self.assertEqual(error, EXPECTED_FORMAT)

    def test_rejects_unknown_param(self) -> None:
        request, error = parse_build_command("build deploy-api tag=v1")
        self.assertIsNone(request)
        self.assertEqual(error, EXPECTED_FORMAT)

    def test_requires_confirm_for_prod(self) -> None:
        request, error = parse_build_command("build deploy-web env=prod")
        self.assertIsNone(request)
        self.assertEqual(error, EXPECTED_FORMAT)

    def test_accepts_confirm_for_prod(self) -> None:
        request, error = parse_build_command("build deploy-web env=prod confirm=yes")
        self.assertIsNotNone(request)
        self.assertIsNone(error)
        self.assertEqual(request.params, {"env": "prod"})

    def test_forwards_allowed_params_only(self) -> None:
        queued = {}

        def fake_trigger(pipeline: str, job: str, params: dict[str, str]) -> None:
            queued["pipeline"] = pipeline
            queued["job"] = job
            queued["params"] = params

        message = handle_slack_command(
            "build smoke-tests branch=feature/foo version=1.2.3",
            jenkins_trigger=fake_trigger,
        )

        self.assertEqual(queued["pipeline"], "test-pipeline")
        self.assertEqual(queued["job"], "smoke-tests")
        self.assertEqual(queued["params"], {"branch": "feature/foo", "version": "1.2.3"})
        self.assertIn("Queued `test-pipeline` build.", message)
        self.assertIn("Job: `smoke-tests`", message)


if __name__ == "__main__":
    unittest.main()
