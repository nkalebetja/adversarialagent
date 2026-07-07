import os
import shutil
import subprocess
import time
import stat
from behave.__main__ import main as behave_main

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FEATURES_PATH = os.path.join(PROJECT_ROOT, "features")
ALLURE_RESULTS = os.path.join(PROJECT_ROOT, "allure-results")
ALLURE_REPORT = os.path.join(PROJECT_ROOT, "allure_report")
ALLURE_EXE = r"C:\Users\nkale\scoop\shims\allure.cmd"


def _on_rm_error(func, path, exc_info):
    """Handle read-only files and transient access issues on Windows.

    - Clears read-only attribute and retries the failed operation.
    """
    try:
        os.chmod(path, stat.S_IWRITE)
    except Exception:
        pass
    try:
        func(path)
    except Exception:
        pass


def safe_rmtree(path: str, *, retries: int = 3, delay_s: float = 0.3) -> None:
    """Robustly remove a directory tree, tolerant of Windows locks/OneDrive.

    Retries a few times, handling read-only files.
    """
    if not os.path.exists(path):
        return
    for attempt in range(retries):
        try:
            shutil.rmtree(path, onerror=_on_rm_error)
            return
        except PermissionError:
            time.sleep(delay_s)
        except OSError:
            time.sleep(delay_s)
    # Last attempt; if it still fails, leave it and continue
    try:
        shutil.rmtree(path, onerror=_on_rm_error)
    except Exception:
        pass


if os.path.exists(ALLURE_RESULTS):
    safe_rmtree(ALLURE_RESULTS)
os.makedirs(ALLURE_RESULTS, exist_ok=True)

options = [
    FEATURES_PATH,
    "-f", "allure_behave.formatter:AllureFormatter",
    "-o", ALLURE_RESULTS,
    "--no-capture",
    "--no-capture-stderr",
    "--no-logcapture",
]

exit_code = behave_main(options)

# Allow skipping Allure operations during interactive debugging
if not os.getenv("SKIP_ALLURE"):
    if os.path.exists(ALLURE_REPORT):
        safe_rmtree(ALLURE_REPORT)
    subprocess.run([ALLURE_EXE, "generate", ALLURE_RESULTS, "-o", ALLURE_REPORT, "--clean"])
    subprocess.run([ALLURE_EXE, "open", ALLURE_REPORT])

exit(exit_code)
