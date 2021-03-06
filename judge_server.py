import binascii
import os
import signal
import pymysql
import MySQLdb
import subprocess
import sys
import time
import yaml

def send(ofp, lname, rname):
	assert os.system('cd /run/shm; ln -s \'%s\' \'%s\'; tar ch \'%s\' | gzip -1 > judge_server.tgz' % (os.path.realpath(lname), rname, rname)) == 0
	with open('/run/shm/judge_server.tgz', 'rb') as fp: b = fp.read()
	os.remove('/run/shm/%s' % rname)
	os.remove('/run/shm/judge_server.tgz')
	b = binascii.hexlify(b)
	ofp.write(('%10d' % len(b)).encode())
	ofp.write(b)
	ofp.flush()

def work(sid, pid, lng, serv):
	print(sid, pid, lng, file = sys.stderr)
        p = subprocess.Popen(['ssh', serv, 'export PATH=$PATH:/home/butler; butler'], stdin = subprocess.PIPE, stdout = subprocess.PIPE)
	ifp = p.stdout
	ofp = p.stdin
	send(ofp, './const.py', 'const.py')
	send(ofp, '../testdata/%d/judge' % pid, 'judge')
	if lng != 0:
		send(ofp, '../submission/%d-0' % sid, 'source')
	else:
		with open('../testdata/%d/source.lst' % pid) as fp:
			i = 0
			for fn in fp.readlines():
				send(ofp, '../submission/%d-%d' % (sid, i), fn[:-1])
				i += 1
	try:
		with open('../testdata/%d/send.lst' % pid) as fp:
			for fn in fp.readlines():
				send(ofp, '../testdata/%d/%s' % (pid, fn[:-1]), fn[:-1])
	except:
		pass
	ofp.write(('%10d' % -lng).encode())
	ofp.flush()
	while True:
		n = int(ifp.read(2))
		if n <= 0: break
		fn = ifp.read(n).decode()
		send(ofp, '../testdata/%d/%s' % (pid, fn), fn)
	score = int(ifp.readline())
	result = int(ifp.readline())
	cpu = int(ifp.readline())
	mem = int(ifp.readline())
	dtl = ifp.read()
	if dtl:
		with open('../submission/%d-z' % sid, 'wb') as fp: fp.write(dtl)
	cursor.execute("UPDATE submissions SET scr=%s, res=%s, cpu=%s, mem=%s WHERE sid=%s" % (score, result, cpu, mem, sid))
	#db.commit()

def prepare(sid, pid, lng):
        address = butler_config['host']
        account = butler_config['user']
        try:
                with open('../testdata/%d/server.py' % pid) as fp:
                        info = eval(fp.read())
                        (address, account) = (info[0][0], info[0][1])
        except:
                pass
        work(sid, pid, lng, '%s@%s' % (account, address))

def main():
	while True:
		cursor.execute('SELECT sid, pid, lng FROM submissions WHERE res = 0 ORDER BY sid LIMIT 1')
		row = cursor.fetchone()
		if row:
			prepare(int(row[0]), int(row[1]), int(row[2]))
		else:
			time.sleep(butler_config['period'])

assert __name__ == '__main__'

with open('_config.yml', 'r') as config_file:
	config = yaml.load(config_file.read())
	db_config = config['DATABASE']
	butler_config = config['BUTLER']
	db = MySQLdb.connect(host=db_config['host'], user=db_config['user'], passwd=db_config['password'], db=db_config['database'])
	cursor = db.cursor()
	main()
