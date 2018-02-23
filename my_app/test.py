

# from forex_python.converter import CurrencyRates 
from lib import converter 
c = converter.CurrencyRates()
print (c.get_rate('USD','EUR'))
