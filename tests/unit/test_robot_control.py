import pytest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from robot_control import RobotControlWidget


@pytest.fixture(scope="module")
def app():
    inst = QApplication.instance()
    if inst is None:
        inst = QApplication([])
    return inst


@pytest.fixture()
def widget(app):
    w = RobotControlWidget()
    w.pause_timers()
    return w


def test_run_cmd_uses_env_cache(widget):
    with patch("robot_control.run_cmd") as mock_run:
        mock_run.return_value = ("out", "", 0)
        widget._run_cmd("echo hi", timeout=5)
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "echo hi"
        assert mock_run.call_args[0][1] == widget.ros_setup
        assert mock_run.call_args[0][2] == widget.ws_setup
        assert mock_run.call_args.kwargs.get("timeout") == 5


def test_emergency_stop_single_subprocess(widget):
    with patch.object(widget, "_run_cmd") as mock_run:
        widget.emergency_stop()
        assert mock_run.call_count == 1
        cmd = mock_run.call_args[0][0]
        assert cmd.count("rostopic pub -1") == 3
        assert "linear: {x: 0" in cmd
        assert widget.cmd_vel_topic in cmd


def test_emergency_stop_zeroes_velocity(widget):
    widget.linear = 0.5
    widget.angular = 0.3
    with patch.object(widget, "_run_cmd"):
        widget.emergency_stop()
    assert widget.linear == 0.0
    assert widget.angular == 0.0


def test_publish_velocity_zero_skipped(widget):
    widget.linear = 0.0
    widget.angular = 0.0
    with patch.object(widget, "_run_cmd") as mock_run:
        widget._publish_velocity()
        mock_run.assert_not_called()


def test_publish_velocity_nonzero_published(widget):
    widget.linear = 0.5
    widget.angular = 0.0
    with patch.object(widget, "_run_cmd") as mock_run:
        widget._publish_velocity()
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "linear: {x: 0.5" in cmd
        assert widget.cmd_vel_topic in cmd


def test_detect_topics_parses_output(widget):
    with patch.object(widget, "_run_cmd",
                      return_value=("/cmd_vel\n/mobile_base/cmd_vel\n", "", 0)):
        topics = widget._detect_topics()
        assert topics == ["/cmd_vel", "/mobile_base/cmd_vel"]


def test_detect_topics_empty_output(widget):
    with patch.object(widget, "_run_cmd", return_value=("", "", 0)):
        assert widget._detect_topics() == []


def test_auto_detect_uses_cmd_vel(widget):
    widget.cmd_vel_topic = "/other"
    with patch.object(widget, "_detect_topics",
                      return_value=["/cmd_vel", "/robot/cmd_vel"]), \
         patch("robot_control.QMessageBox.information"):
        widget._auto_detect_topic()
    assert widget.cmd_vel_topic == "/cmd_vel"


def test_auto_detect_no_topics_shows_message(widget):
    with patch.object(widget, "_detect_topics", return_value=[]), \
         patch("robot_control.QMessageBox.information") as mock_info:
        widget._auto_detect_topic()
    mock_info.assert_called_once()


def test_auto_detect_without_cmd_vel_asks_selection(widget):
    widget.cmd_vel_topic = "/cmd_vel"
    with patch.object(widget, "_detect_topics",
                      return_value=["/robot/cmd_vel", "/nav/cmd_vel"]), \
         patch("robot_control.QInputDialog.getItem",
               return_value=("/robot/cmd_vel", True)):
        widget._auto_detect_topic()
    assert widget.cmd_vel_topic == "/robot/cmd_vel"


def test_set_topic_uses_dropdown(widget):
    with patch.object(widget, "_detect_topics",
                      return_value=["/cmd_vel", "/robot/cmd_vel"]), \
         patch("robot_control.QInputDialog.getItem",
               return_value=("/robot/cmd_vel", True)):
        widget._set_topic()
    assert widget.cmd_vel_topic == "/robot/cmd_vel"


def test_set_topic_manual_input(widget):
    with patch.object(widget, "_detect_topics", return_value=["/cmd_vel"]), \
         patch("robot_control.QInputDialog.getItem",
               return_value=("/my_topic", True)):
        widget._set_topic()
    assert widget.cmd_vel_topic == "/my_topic"
