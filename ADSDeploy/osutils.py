import os
import threading
import subprocess
import signal

def cmd(cmd, inputv=None, cwd=None, max_wait=None):
    """Runs a command in the console and returns back the STDOUT/STDERR"""
    try:
        p = subprocess.Popen(cmd, shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            close_fds=True,
            preexec_fn=os.setsid
            )
    except Exception, e:
        raise e
    
    timer = None
    if max_wait:
        def run(pro):
            os.killpg(os.getpgid(pro.pid), signal.SIGTERM)
        timer = threading.Timer(max_wait, run, args=[p])
        
    
    if inputv:
        p.communicate(inputv)
        
    retcode = p.wait()
    
    if timer and timer.isAlive():
        timer.cancel()

    class Object(object):
        def __str__(self):
            return 'cmd: {0}\nout:{1}\nerr:{2}\nretcode:{3}'.format(self.cmd, 
                                                                    self.out, 
                                                                    self.err, 
                                                                    self.retcode)

    out = Object()
    setattr(out, 'cmd', cmd)
    setattr(out, 'out', p.stdout.read())
    setattr(out, 'err', p.stderr.read())
    setattr(out, 'retcode', retcode)

    p.stdout.close()
    p.stderr.close()
    p.stdin.close()
    
    if retcode:
        raise Exception(dict(cmd=cmd, out=out.out, err=out.err, retcode=out.retcode))
    
    return out


class Executioner(object):
    def __init__(self, python_virtualenv, home_folder, max_wait):
        self.root = home_folder
        self.pyenv = python_virtualenv
        self.max_wait = max_wait
        
    def cmd(self, command, inputv=None):
        """Will always run the command with activated python virtualenv
        and inside the specified folder."""
        
        return cmd("bash -c \"source {0} && {1}\"".format(self.pyenv, command), inputv, cwd=self.root)