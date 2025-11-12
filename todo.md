a modular system that tracks deals that can be found on internet if they fullfill certain criteria, it periodically checks if new deals were added and checks if there were changes like decreased price in the existing deals
data is obtained by scraping websites, there will be several modules, each able to deal with the format of specific website, for start we will only be using bazos.sk and namely in categories 
https://auto.bazos.sk/bmw/ - we will be looking for BMW E36, E46, E39 with a 6 cylinder petrol engine and manual transmission (6 valec, benzin, manualna prevodovka)

and in 
https://reality.bazos.sk/predam/pozemok/
https://reality.bazos.sk/predam/dom/
https://reality.bazos.sk/predam/chata/
we will be looking for land, houses or cottages with a large plot of land of at least 4 hectares or 40000 square meters and price below 400000EUR

we will be storing deals fullfilling our criteria in a postgresql database and will track the date they were added and a history of price changes and dates when they disappear so we can judge how long it takes for these to sell

configuration of parameters for search should be done via json file, this will be run in a console using cron periodically so no elaborate output is needed just some indication what is going on and if something new or a change was detected, 
more human readable format will be done later in a consuming web application, this is just about getting and maintaining the data

please research the format of data on the websites
suggest mechanism for obtaining the data, how to store it, what the filtering system should be
