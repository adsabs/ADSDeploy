from . import app
from .models import KeyValue
from .pipeline.deploy import create_executioner
import time

def cleanup_environments():
    """Will terminate any testing environments that are older than
    AFTER_DEPLOY_CLEANUP_TIME (for the application that was deployed)
    """            
    with app.session_scope() as session:
        for u in session.query(KeyValue).filter(filter(KeyValue.column.ilike("%last-used"))).all():
            appl, env, k = u.key.split('.')
            if time.time() + 1 - float(u.value) > app.config.get('AFTER_DEPLOY_CLEANUP_TIME', 50*60):
                x = create_executioner({'application': appl, 'environment': env})
                r = x.cmd("./find-env-by-attr url testing")
                to_terminate = []
                for env in r.out.split():
                    parts = env.split()
                    to_terminate.append(parts[4])
                for x in to_terminate:
                    x.cmd('eb terminate --force --nohang {0}'.format(x))
                session.delete(u)


