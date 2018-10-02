from celery import Celery

celery_app = Celery('dtools', backend='rpc://', broker='pyamqp://',
                    include=['gonet.ontol', 'gonet.graph'])

celery_app.conf.update({'worker_hijack_root_logger':False})
