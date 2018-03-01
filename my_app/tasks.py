from celery import task
from my_app.models import Order as OrderList
from datetime import date, time, datetime


@task
def test_celery():
    timeLimit = 5
    orders = OrderList.objects.all()
    out = open('orders.txt', 'a')
    for order in orders:
        # check if X minutes have elapsed and then complete due orders
        now = datetime.now().strftime('%H:%M:%S')
        now = datetime.strptime(now, '%H:%M:%S').time()
        elapsedTime = datetime.combine(date.min, now) - datetime.combine(date.min, order.time)

        out.write(str(elapsedTime)+' ')
    out.close


