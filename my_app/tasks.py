from celery import task

@task
def test_celery():
    out = open('testt.txt', 'a')
    out.write('ahaha')
    out.close
