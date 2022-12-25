import logging
import os
import subprocess
from typing import Any, Dict, Optional, Union

from auth import AuthSession
from common import AppResult
from settings import PASS_STORE_DIR

logger = logging.getLogger(__name__)


class PassApp:
    APP_CODE = "PASS"
    GPG_EXT = "gpg"

    def __init__(self):
        self._passes_data = {}
        self.auth = AuthSession()

    def authorize(self, passphrase: str) -> bool:
        return self.auth.try_authorize(passphrase).status

    @property
    def is_authorized(self) -> bool:
        return self.auth.is_active

    def list_passes(self, subdir: Union[str, None]) -> Dict[str, list]:
        return self._passes_data.get(subdir, self._fill_passes_data(subdir))

    def show(self, pass_path: Optional[str] = None) -> Union[str, None]:
        if self.auth.is_active:
            return self._acquire_pass_data(pass_path)

    def add_new_pass(self, pass_path: str, passphrase: str) -> AppResult:
        if self.is_pass_exists(pass_path):
            result = AppResult(f"Pass path already exists: {pass_path}", False)
            logger.error(result)
            return result

        result = self._insert_pass_data(pass_path, passphrase)
        return AppResult(result)

    def edit_overwrite(self, pass_path: str, passphrase: str) -> AppResult:
        if not self.auth.is_active:
            return AppResult(False, "Pass session not activated")

        if not self.is_pass_exists(pass_path):
            result = AppResult(False, f"Pass path does not exist: {pass_path}")
            logger.error(result)
            return result

        result = self._insert_pass_data(pass_path, passphrase)
        return AppResult(result)

    def edit_append(self, pass_path: str, passphrase: str) -> AppResult:
        if not self.auth.is_active:
            return AppResult(False, "Pass session not activated")

        if not self.is_pass_exists(pass_path):
            result = AppResult(False, f"Pass path does not exist: {pass_path}")
            logger.error(result)
            return result

        pass_data = self._acquire_pass_data(pass_path)
        result = self._insert_pass_data(pass_path, f"{pass_data}{passphrase}")
        return AppResult(result)

    def is_pass_exists(self, pass_path: str) -> bool:
        try:
            if self._get_pass_filepath(pass_path).endswith(self.GPG_EXT):
                return True
        except PassPathNotExists:
            pass

        return False

    def _fill_passes_data(self, path: str) -> Dict[str, Any]:
        lsdir = self._get_subdir_path(path)
        if not lsdir:
            return {}

        passes_data = {"passfiles": [], "passsubdirs": []}

        pass_list = subprocess.check_output(rf"ls {lsdir}", shell=True).decode("utf-8")
        for pass_ in pass_list.split("\n"):
            if pass_.endswith(".gpg"):
                pass_ = os.path.splitext(pass_)[0]
                passes_data["passfiles"].append(pass_)
            elif pass_:
                passes_data["passsubdirs"].append(pass_)

        self._passes_data[path] = passes_data

        return passes_data

    def _insert_pass_data(self, pass_path: str, pass_data: str) -> bool:
        if not pass_path or not pass_data:
            return False

        cmd = rf"pass insert -e {pass_path}"
        try:
            subprocess.check_output(
                cmd, universal_newlines=True, shell=True, input=pass_data
            )
        except Exception as exc:
            logger.error(f"Some error occured on updating pass data: {exc}")
            return False

        return True

    def _acquire_pass_data(self, pass_path: str) -> Union[str, None]:
        try:
            pass_file = self._get_pass_filepath(pass_path)
        except (PassPathNotExists, PassPathEmptyError):
            return None

        try:
            cmd = rf"echo $GPG_PASSPHRASE | gpg -d --pinentry-mode loopback --passphrase-fd 0 {pass_file}"
            pass_data = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except Exception as exc:
            logger.error("Error occured while getting pass data: ", str(exc))
            return None

        return pass_data

    def _get_subdir_path(self, rel_path: str) -> Union[str, None]:
        if not rel_path:
            rel_path = ""
        elif rel_path.startswith(os.path.sep):
            rel_path = rel_path[1:]

        lsdir = os.path.join(PASS_STORE_DIR, rel_path)
        if os.path.exists(lsdir):
            return lsdir

    def _get_pass_filepath(self, pass_path: str) -> str:
        if not pass_path:
            raise PassPathEmptyError

        pass_filepath = os.path.join(PASS_STORE_DIR, f"{pass_path}.{self.GPG_EXT}")
        if not os.path.isfile(pass_filepath):
            raise PassPathNotExists

        return pass_filepath


class PassPathEmptyError(Exception):
    def __str__(self) -> str:
        return "Empty pass path"


class PassPathNotExists(Exception):
    def __str__(self) -> str:
        return "Pass path doesn't exists"


PASS_APP = PassApp()
del PassApp
