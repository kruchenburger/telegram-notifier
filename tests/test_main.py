import os
import tempfile

from telegram_notifier.main import set_action_output


def test_set_action_output_writes_to_file() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_path = f.name

    try:
        os.environ["GITHUB_OUTPUT"] = temp_path
        set_action_output("status", "Successfully delivered")

        with open(temp_path, encoding="UTF-8") as f:
            content = f.read()

        assert content == "status=Successfully delivered\n"
    finally:
        os.unlink(temp_path)
        del os.environ["GITHUB_OUTPUT"]


def test_set_action_output_multiple_outputs() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_path = f.name

    try:
        os.environ["GITHUB_OUTPUT"] = temp_path
        set_action_output("status", "ok")
        set_action_output("message_id", "12345")

        with open(temp_path, encoding="UTF-8") as f:
            content = f.read()

        assert content == "status=ok\nmessage_id=12345\n"
    finally:
        os.unlink(temp_path)
        del os.environ["GITHUB_OUTPUT"]
