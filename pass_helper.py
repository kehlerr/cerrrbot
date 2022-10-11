
import os
import subprocess
from typing import Optional, Union

from settings import PASS_STORE_DIR, GPG_EXT


class PassPathEmptyError(Exception):
    def __str__(self) -> str:
        return "Empty pass path"


class PassPathNotExists(Exception):
    def __str__(self) -> str:
        return "Pass path doesn't exists"


class PassApp:
    APP_CODE = "PASS"

    def __init__(self):
        self.requested_pass = None

    def list_passes(self, subdir: Union[str, None]) -> str:

        if subdir is None:
            subdir = "/"

        lsdir = os.path.join(PASS_STORE_DIR, subdir)

        if not os.path.exists(lsdir):
            return "Pass path not exists"

        pass_list = subprocess.check_output(rf"ls {lsdir}", shell=True).decode("utf-8")
        answer = []
        for pass_ in pass_list.split("\n"):
            if pass_.endswith(".gpg"):
                pass_ = os.path.splitext(pass_)[0]
                pass_ = f"<code>{pass_}</code>"
            answer.append(pass_)

        answer = "\n".join(answer)

        return answer


    def show(self, pass_path: Optional[str] = None) -> str:

        pass_path = pass_path or self.requested_pass

        try:
            pass_file = self._get_pass_filepath(pass_path)
        except Exception as exc:
            return f"{str(exc)}, {pass_path}"

        cmd = rf"echo $GPG_PASSPHRASE | gpg -d --pinentry-mode loopback --passphrase-fd 0 {pass_file}"
        pass_ = subprocess.check_output(cmd, shell=True).decode("utf-8")
        if pass_:
            answer = f"<tg-spoiler>{pass_}</tg-spoiler>"
        else:
            answer = "Something went wrong..."

        return answer


    def edit(self, pass_path: str) -> str:
        try:
            pass_filepath = self._get_pass_filepath(pass_path)
        except Exception as exc:
            return f"{str(exc)}, {pass_path}"


    def _get_pass_filepath(self, pass_path: str) -> Union[str, None]:
        if not pass_path:
            raise PassPathEmptyError

        pass_file = os.path.join(PASS_STORE_DIR, f"{pass_path}.{GPG_EXT}")
        if not os.path.exists(pass_file):
            raise PassPathNotExists

        return pass_file


PASS_APP = PassApp()
del PassApp