import os
import subprocess
from typing import Optional, Union, Dict, Any

from settings import PASS_STORE_DIR, GPG_EXT


class PassApp:
    _passes_data: dict

    APP_CODE = "PASS"

    def list_passes(self, subdir: Union[str, None]) -> Dict[str, list]:
        return self._passes_data.get(subdir, self._fill_passes_data(subdir))

    def show(self, pass_path: Optional[str] = None) -> Union[str, None]:
        return self._acquire_pass_data(pass_path)
       #if pass_:
       #    answer = f"<tg-spoiler>{pass_}</tg-spoiler>"
       #else:
       #    answer = "Something went wrong..."

    def add_new_pass(self, pass_path: str, passphrase: str) -> bool:
        if self.is_pass_exists(pass_path):
            # TODO: logger.error
            return False

        return self._insert_pass_data(pass_path, passphrase)

    def edit_overwrite(self, pass_path: str, passphrase: str) -> bool:
        if not self.is_pass_exists(pass_path):
            # TODO: logger.error
            return False

        return self._insert_pass_data(pass_path, passphrase)

    def edit_append(self, pass_path: str, passphrase: str) -> bool:
        if not self.is_pass_exists(pass_path):
            # TODO: logger.error
            return False

        pass_data = self._acquire_pass_data(pass_path)
        return self._insert_pass_data(pass_path, f"{pass_data}{passphrase}")

    def is_pass_exists(self, pass_path: str) -> bool:
        try:
            if self._get_pass_filepath(pass_path).endswith(GPG_EXT):
                return True
        except PassPathNotExists:
            pass

        return False

    def _fill_passes_data(self, path: str) -> Dict[Any]:
        lsdir = self._get_subdir_path(path)
        if not lsdir:
            return {}

        passes_data = {
            "passfiles": [],
            "passsubdirs": []
        }

        pass_list = subprocess.check_output(rf"ls {lsdir}", shell=True).decode("utf-8")
        for pass_ in pass_list.split("\n"):
            if pass_.endswith(".gpg"):
                pass_ = os.path.splitext(pass_)[0]
                #pass_ = f"<code>{pass_}</code>"
                passes_data["passfiles"].append(pass_)
            else:
                passes_data["passsubdirs"].append(pass_)

        self._passes_data[path] = passes_data

        return passes_data

    def _insert_pass_data(self, pass_path: str, pass_data: str) -> bool:
        if not pass_path or not pass_data:
            return False

        cmd = rf"pass insert -e {pass_path}"
        try:
            print(pass_data)
            saved_passphrase = subprocess.check_output(cmd, universal_newlines=True, shell=True, input=pass_data)
        except Exception as exc:
            pass    # TODO: logger.error
            return False

        return True

    def _acquire_pass_data(self, pass_path: str) -> Union[str, None]:
        try:
            pass_file = self._get_pass_filepath(pass_path)
        except (PassPathNotExists, PassPathEmptyError) as exc:
            return None

        try:
            cmd = rf"echo $GPG_PASSPHRASE | gpg -d --pinentry-mode loopback --passphrase-fd 0 {pass_file}"
            pass_data = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except Exception as exc:
            return None

        return pass_data

    def _get_subdir_path(rel_path: str) -> Union[str, None]
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

        pass_filepath = os.path.join(PASS_STORE_DIR, f"{pass_path}.{GPG_EXT}")
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
