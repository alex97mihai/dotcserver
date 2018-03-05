from celery import task
from my_app.models import Order as OrderList
from my_app.models import CompleteOrders
from datetime import date, time, datetime, timedelta
from django.contrib.auth.models import User as dbUser


@task
def test_celery():
    # wait 5 minutes before automatically completing order
    timeLimit = timedelta(minutes = 1)
    
    orders = OrderList.objects.all()
    out = open('complete_orders.txt', 'a')
    for order in orders:
        # get elapsed time for order
        now = datetime.now().strftime('%H:%M:%S')
        now = datetime.strptime(now, '%H:%M:%S').time()
        elapsedTime = datetime.combine(date.min, now) - datetime.combine(date.min, order.time)
        
        if elapsedTime > timeLimit:
            user = dbUser.objects.get(username=str(order.user))

            print(user)
            
            balance = { "EUR":0, "USD":0}

            balance[str(order.home_currency)] = order.home_currency_amount * -1
            balance[str(order.target_currency)] = order.target_currency_amount 

            user.profile.USD = user.profile.USD + balance["USD"]
            user.profile.EUR = user.profile.EUR + balance["EUR"]
            user.save()

            print(balance)

            # save order to external record and delete from db
            out.write('%s;%s;%s;%s;%s;%s;%s;%s\n' % (user.username, str(order.date), str(order.time), order.home_currency, str(order.home_currency_amount), str(order.rate), order.target_currency, str(order.target_currency_amount)) )
            
            CompleteOrder = CompleteOrders(user=order.user, date=order.date, time=order.time, home_currency=order.home_currency, home_currency_amount=order.home_backup, rate=order.rate, target_currency=order.target_currency, target_currency_amount=order.target_backup, status='complete')
            CompleteOrder.save()
            order.delete()
    
    out.close


