from celery import task
from my_app.models import Order
from datetime import date, time, datetime


@task
def test_celery():
    test = Order.objects.all()
    test_order = datetime.combine(date.min, test[1].time) - datetime.combine(date.min, test[0].time) 
    out = open('orders.txt', 'a')
    out.write(str(test_order))
    out.close


