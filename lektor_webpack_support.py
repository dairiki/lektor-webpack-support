import os
import shutil
import subprocess
from pathlib import Path

from lektor.pluginsystem import Plugin
from lektor.reporter import reporter
from lektor.utils import locate_executable
from lektor.utils import portable_popen


class WebpackSupportPlugin(Plugin):
    name = "Webpack Support Plugin"
    description = "Super simple Lektor plugin that runs a webpack watcher"

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        self.webpack_root = Path(self.env.root_path, "webpack")
        self.webpack_process = None

    def is_enabled(self, extra_flags):
        return bool(extra_flags.get("webpack"))

    def get_pkg_manager_bin(self):
        yarn_lock = self.webpack_root / "yarn.lock"
        if yarn_lock.exists():
            yarn_bin = shutil.which("yarn")
            if yarn_bin is not None:
                return yarn_bin
        npm_bin = shutil.which("npm")
        if npm_bin is None:
            raise RuntimeError("can not locate 'npm' executable")
        return npm_bin

    @property
    def webpack_bin(self):
        webpack_bin = self.webpack_root.absolute() / "node_modules/.bin/webpack"
        
    def run_webpack(self, watch=False):
        webpack_root = os.path.join(self.env.root_path, "webpack")
        args = [os.path.join(webpack_root, "node_modules", ".bin", "webpack")]
        if watch:
            args.append("--watch")
        return portable_popen(args, cwd=webpack_root)

    def install_node_dependencies(self):
        pkg_manager = self.get_pkg_manager_bin()
        reporter.report_generic("Running {} install".format(pkg_manager))
        subprocess.run([pkg_manager, "install"], cwd=webpack_root, check=True)

    def on_server_spawn(self, **extra):
        extra_flags = extra.get("extra_flags") or extra.get("build_flags") or {}
        if not self.is_enabled(extra_flags):
            return
        self.install_node_dependencies()
        reporter.report_generic("Spawning webpack watcher")
        self.webpack_process = subprocess.Popen(
            [self.webpack_bin, "--watch"], cwd=self.webpack_root
        )

    def on_server_stop(self, **extra):
        if self.webpack_process is not None:
            reporter.report_generic("Stopping webpack watcher")
            self.webpack_process.kill()

    def on_before_build_all(self, builder, **extra):
        extra_flags = getattr(
            builder, "extra_flags", getattr(builder, "build_flags", None)
        )
        if not self.is_enabled(extra_flags) or self.webpack_process is not None:
            return
        self.install_node_dependencies()
        reporter.report_generic("Starting webpack build")
        subprocess.run([self.webpack_bin], cwd=self.webpack_root, check=True)
        reporter.report_generic("Webpack build finished")
