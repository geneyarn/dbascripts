#!/usr/bin/python
# -*- coding: utf-8 -*-
import datetime
import time
from optparse import OptionParser
import subprocess

class Event:
    trx_id = 0
    event_rows = 0
    trx_time = 0
    trx_size = 0
    trx_start = "2020-01-01 00:00:00"
    start_line = 0
    end_line = 0
    last_committed = 0
    sequence_number = 0
    def __init__(self, trx_id, event_rows,trx_size,trx_time,trx_start,start_line,end_line,last_committed,sequence_number):
        self.trx_id = trx_id
        self.event_rows = event_rows
        self.trx_size =trx_size
        self.trx_time = trx_time
        self.trx_start = trx_start
        self.start_line = start_line
        self.end_line = end_line
        self.last_committed = last_committed
        self.sequence_number =sequence_number

    def __str__(self):
        timeArray = time.localtime(self.trx_start)
        return 'trx %s start at:%s from line: %s to line: %s has %s rows ,size: %s, executed:%s s last_committed: %s sequence_number: %s' \
               % (self.trx_id, time.strftime("%Y--%m--%d %H:%M:%S",timeArray),self.start_line,
                  self.end_line,self.event_rows,self.trx_size,self.trx_time,self.last_committed,self.sequence_number)

def string_toTimestamp(st):
    return time.mktime(time.strptime(st, "%Y%m%d %H:%M:%S"))

def get_top_10_by_rows(event_list):
    sorted_rows = sorted(event_list, key=lambda x: x.event_rows, reverse=True)
    return sorted_rows[:100]


def get_top_10_by_size(event_list):
    sorted_size = sorted(event_list, key=lambda x: x.trx_size,  reverse=True)
    return sorted_size[:100]

def get_top_10_by_time(event_list):
    sorted_time = sorted(event_list, key=lambda x: x.trx_time,  reverse=True)
    return sorted_time[:100]


def get_trx(filename):
    line_no = 0
    res_event_list = []
    first_at = False
    start_line = 0
    end_line = 0
    with open(filename, 'r') as f:
        while True:

            line = f.readline()
            line_no = line_no + 1

            first_time = False
            if not line:
                break
            if "last_committed" in line and "sequence_number" in line:
                l = line.split("\t")
                for i in range(len(l)):
                    if "last_committed" in l[i]:
                        last_committed = l[i].split("=")[1]
                    if "sequence_number" in l[i]:
                        sequence_number = l[i].split("=")[1]
            if "BEGIN" == line.strip():
               # v = Event(0,0,0,0)
                first_at = True
                first_map =True

                first_time = True
                rows = 0
                start_line = line_no

            if line.startswith("#") and first_at:

                start_pos = line.split(' ')[-1]
                first_at = False
            if "end_log_pos" in line and "Table_map" in line and  first_map :
                # 需要修改下获取方式，遍历数组，然后根据关键字去获取值，不能用位置获取
                l = line.split(" ")
                for i in range(len(l)):
                    if l[i] == "server":
                        pos = i
                start_time = line.split(" ")[:pos]
                first_map = False
            if "UPDATE" in line or "INSERT" in line or "DELETE" in line:
                try:
                    rows = rows +1
                except Exception as e:
                    print" rows error"
                    print(line_no)
                    print(line)
            if "end_log_pos" in line and "Xid" in line:
                l = line.split(" ")
                for i in range(len(l)):
                    if l[i] == "end_log_pos":
                        endpos = i+1
                    if l[i] == "server":
                        endtimepos = i
                # 需要修改下获取方式，遍历数组，然后根据关键字去获取值，不能用位置获取
                end_pos = l[endpos]
                xid = l[-1]
                #if transaction use auto commit ,then this end_time is not real time,it's same as begin time,so we need to check affected rows
                # 需要修改下获取方式，遍历数组，然后根据关键字去获取值，不能用位置获取/
                end_time = l[:endtimepos]

            if "COMMIT/*!*/;" in line:
                try:
                    end_line = line_no
                    if len(start_time)==3:
                        s_time = string_toTimestamp("20"+start_time[0][1:] + " " + start_time[2])
                    elif len(start_time)==2:
                        s_time = string_toTimestamp("20" + start_time[0][1:] + " " + start_time[1])
                    if len(end_time) == 3:
                        e_time = string_toTimestamp("20"+end_time[0][1:] + " " + end_time[2])
                    elif len(end_time) ==2:
                        e_time = string_toTimestamp("20" + end_time[0][1:] + " " + end_time[1])
                    exec_time = e_time - s_time
                except Exception as e:
                    print"commit error"
                    print(line_no)
                    print(line)
                    print(e)
                event_rows = rows
                trx_time = exec_time
                trx_size = int(end_pos) - int(start_pos)
                trx_id = xid.strip()
                trx_start = s_time
                res_event_list.append(Event(trx_id,event_rows,trx_size,trx_time,trx_start,start_line,end_line,last_committed,sequence_number))
                first_time = False

    print("------order by rows-------")
    for event in get_top_10_by_rows(res_event_list):
        print event
    print("------order by size-------")

    for event in get_top_10_by_size(res_event_list):
        print event
    print("------order by time-------")

    for event in get_top_10_by_time(res_event_list):
        print event

def opt():
    parser = OptionParser(usage="python bigtrx.py --filename=mysql-bin.006281 --start-datetime=\"2021-06-17 12:23:06\" --stop-datetime=\"2021-06-17 12:23:08\" ",
                  description="get offline binlog top 10 big trx ")
    parser.add_option( "--filename", dest="filename", action="store",
                  help="binlog file name", metavar="mysqlbinlog.000001")

    parser.add_option( "--start-datetime", dest="starttime", action="store",
                  help="start time")
    parser.add_option("--stop-datetime", dest="stoptime", action="store",
                  help="stop datetime")
    parser.add_option("--start-position", dest="startpos", action="store",
                      help="start position")
    parser.add_option("--stop-position", dest="stoppos", action="store",
                      help="stop postion")

    (options, args) = parser.parse_args()
    return options


if __name__ == '__main__':
    optoins = opt()
#     TODO: collect group commit information ,see there are how many groups and how many transactions in group between  certain time
    if optoins.starttime and optoins.stoptime:
        cmd = 'mysqlbinlog -v -v --base64-output=decode-rows  --start-datetime="%s" --stop-datetime="%s"  %s > out.txt' %(optoins.starttime,optoins.stoptime,optoins.filename)
    elif optoins.startpos and optoins.stoppos:
        cmd = 'mysqlbinlog -v -v --base64-output=decode-rows  --start-position="%s" --stop-position="%s"  %s > out.txt' %(optoins.startpos,optoins.stoppos,optoins.filename)
    else:
        print("pls input start time and end time or start position and end position")
        exit(-1)

    r = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    res_t = r.stdout.read().decode("utf-8")
    res_e = r.stderr.read().decode("utf-8")
    print(res_t)
    if res_e :
        print(res_e)
        exit(-1)

    get_trx("out.txt")
    print("\n")
    print("you can get trx information by using command like  sed -n '329,343p' out.txt")
