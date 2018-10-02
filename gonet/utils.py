import time
import logging
from threading import Thread
from django.conf import settings

log = logging.getLogger(__name__)

def app_works(app, taskname=None, jobid='NA'):
    conn = app.connection()
    i = app.control.inspect()
    try:
        conn.connect()
        conn.release()
        if taskname:
            tasks_dict = i.registered_tasks()
            if tasks_dict:
                for host, tasks in tasks_dict.items():
                    if taskname in tasks:
                        return True
                    else:
                        return False
            else:
                return False    
        else:
            if app.control.inspect().stats():
                return True
            else:
                return False
    except ConnectionRefusedError:
        log.warn('Got ConnectionRefusedError', extra={'jobid':jobid})
        return False
    except ConnectionResetError:
        log.warn('Got ConnectionResetError', extra={'jobid':jobid})
        return False
    

def thread_func(function):
    def decorator(*args, **kwargs):
        jobid = args[0].id
        if settings.TESTING or settings.SHELLENV:
            log.info('In testing environment so running function '\
                     +function.__name__+' in the main thread',
                     extra={'jobid':jobid})
            function(*args, **kwargs)
        else:
            log.info('In server environment so running function '\
                     +function.__name__+' in a separate thread',
                     extra={'jobid':jobid})
            t = Thread(target = function, args=args, kwargs=kwargs)
            t.daemon = True
            t.start()
    return decorator

def process_signature(s, jobid=None, celery=True, serializer='json'):
    if 'jobid' in s.kwargs:
        jobid=s.kwargs['jobid']

    log.info('inside process signature for '+s.name, extra={'jobid':jobid})
    if celery and app_works(s.app, s.name, jobid=jobid):
        r = s.apply_async(serializer=serializer)
        cnt = 0
        while not r.ready():
            cnt += 1
            log.debug('Waiting for task to complete ...', extra={'jobid':jobid})
            time.sleep(2)
            if (cnt % 30 == 10):
                if not app_works(s.app, jobid=jobid):
                    log.debug('Interrupting after too many attempts '\
                              +'since Celery app is not reachable.', extra={'jobid':jobid})
                    log.error('Celery is not available. ', extra={'jobid':jobid})
                    r.revoke()
                    r = s.apply()
                    break
    else:
        log.info('Running '+s.name+' without Celery.', extra={'jobid':jobid})
        r = s.apply()
    if r.status != 'SUCCESS':
        log.error(s.name+' task failed', extra={'jobid':jobid})
        
    if issubclass(type(r.result), Exception):
        raise r.result
    return r.result
