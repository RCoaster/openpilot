import pytest
import datetime
import json
import os
import threading
import time
import uuid

from openpilot.common.params import Params, ParamKeyFlag, UnknownKeyName

class TestParams:
  def setup_method(self):
    self.params = Params()

  def test_params_put_and_get(self):
    self.params.put("DongleId", "cb38263377b873ee")
    assert self.params.get("DongleId") == "cb38263377b873ee"

  def test_params_non_ascii(self):
    st = b"\xe1\x90\xff"
    self.params.put("CarParams", st)
    assert self.params.get("CarParams") == st

  def test_params_get_cleared_manager_start(self):
    self.params.put("CarParams", "test")
    self.params.put("DongleId", "cb38263377b873ee")
    assert self.params.get("CarParams") == b"test"

    undefined_param = self.params.get_param_path(uuid.uuid4().hex)
    with open(undefined_param, "w") as f:
      f.write("test")
    assert os.path.isfile(undefined_param)

    self.params.clear_all(ParamKeyFlag.CLEAR_ON_MANAGER_START)
    assert self.params.get("CarParams") is None
    assert self.params.get("DongleId") is not None
    assert not os.path.isfile(undefined_param)

  def test_params_two_things(self):
    self.params.put("DongleId", "bob")
    self.params.put("AthenadPid", "123")
    assert self.params.get("DongleId") == "bob"
    assert self.params.get("AthenadPid") == "123"

  def test_params_get_block(self):
    def _delayed_writer():
      time.sleep(0.1)
      self.params.put("CarParams", "test")
    threading.Thread(target=_delayed_writer).start()
    assert self.params.get("CarParams") is None
    assert self.params.get("CarParams", True) == b"test"

  def test_params_unknown_key_fails(self):
    with pytest.raises(UnknownKeyName):
      self.params.get("swag")

    with pytest.raises(UnknownKeyName):
      self.params.get_bool("swag")

    with pytest.raises(UnknownKeyName):
      self.params.put("swag", "abc")

    with pytest.raises(UnknownKeyName):
      self.params.put_bool("swag", True)

  def test_remove_not_there(self):
    assert self.params.get("CarParams") is None
    self.params.remove("CarParams")
    assert self.params.get("CarParams") is None

  def test_get_bool(self):
    self.params.remove("IsMetric")
    assert not self.params.get_bool("IsMetric")

    self.params.put_bool("IsMetric", True)
    assert self.params.get_bool("IsMetric")

    self.params.put_bool("IsMetric", False)
    assert not self.params.get_bool("IsMetric")

    self.params.put("IsMetric", "1")
    assert self.params.get_bool("IsMetric")

    self.params.put("IsMetric", "0")
    assert not self.params.get_bool("IsMetric")

  def test_put_non_blocking_with_get_block(self):
    q = Params()
    def _delayed_writer():
      time.sleep(0.1)
      Params().put_nonblocking("CarParams", "test")
    threading.Thread(target=_delayed_writer).start()
    assert q.get("CarParams") is None
    assert q.get("CarParams", True) == b"test"

  def test_put_bool_non_blocking_with_get_block(self):
    q = Params()
    def _delayed_writer():
      time.sleep(0.1)
      Params().put_bool_nonblocking("CarParams", True)
    threading.Thread(target=_delayed_writer).start()
    assert q.get("CarParams") is None
    assert q.get("CarParams", True) == b"1"

  def test_params_all_keys(self):
    keys = Params().all_keys()

    # sanity checks
    assert len(keys) > 20
    assert len(keys) == len(set(keys))
    assert b"CarParams" in keys

  def test_params_default_init_value(self):
    assert self.params.get_default_value("LanguageSetting")
    assert self.params.get_default_value("LongitudinalPersonality")
    assert not self.params.get_default_value("LiveParameters")

  def test_params_get_type(self):
    # json
    self.params.put("ApiCache_FirehoseStats", json.dumps({"a": 0}))
    assert self.params.get("ApiCache_FirehoseStats") == {"a": 0}

    # int
    self.params.put("BootCount", str(1441))
    assert self.params.get("BootCount") == 1441

    # bool
    self.params.put("AdbEnabled", "1")
    assert self.params.get("AdbEnabled")

    # time
    now = datetime.datetime.now(datetime.UTC)
    self.params.put("InstallDate", str(now))
    assert self.params.get("InstallDate") == now

  def test_params_get_default(self):
    now = datetime.datetime.now(datetime.UTC)
    self.params.remove("InstallDate")
    assert self.params.get("InstallDate") is None
    assert self.params.get("InstallDate", default=now) == now

    self.params.put("BootCount", "1xx1")
    assert self.params.get("BootCount") is None
    assert self.params.get("BootCount", default=1441) == 1441
