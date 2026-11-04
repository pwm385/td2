# -*- coding: utf-8 -*-
import subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
xml = r"D:\鱼池\全境封锁2掉落站\task_tmp.xml"
r = subprocess.run(["schtasks", "/Create", "/TN", "TD2_Loot_Daily", "/XML", xml, "/F"],
                   capture_output=True)
print("rc:", r.returncode)
print("out:", r.stdout.decode("gbk", "replace").strip())
print("err:", r.stderr.decode("gbk", "replace").strip())
q = subprocess.run(["schtasks", "/Query", "/TN", "TD2_Loot_Daily", "/FO", "LIST"],
                   capture_output=True)
print("---- 查询 ----")
print(q.stdout.decode("gbk", "replace").strip()[:800] or q.stderr.decode("gbk","replace"))
