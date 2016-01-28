
import subprocess

def cmd(cmd, inputv=None, cwd=None):
    """Runs a command in the console and returns back the STDOUT/STDERR"""
    try:
        p = subprocess.Popen(cmd, shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            close_fds=True)
    except Exception, e:
        raise e
    
    if inputv:
        p.communicate(inputv)
    retcode = p.wait()

    class Object(object): pass

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
    def __init__(self, python_virtualenv, home_folder):
        self.root = home_folder
        self.pyenv = python_virtualenv
        
    def cmd(self, command, inputv=None):
        """Will always run the command with activated python virtualenv
        and inside the specified folder."""
        
        return cmd("bash -c \"source {0} && {1}\"".format(self.pyenv, command), inputv, cwd=self.root)