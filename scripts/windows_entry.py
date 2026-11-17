"""Windows 打包入口：使用绝对导入启动应用。"""

from litmgr.__main__ import main
import sys


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--check-bundle":
        from check_windows_bundle import check_bundle
        raise SystemExit(check_bundle(sys.argv[2]))
    raise SystemExit(main())
