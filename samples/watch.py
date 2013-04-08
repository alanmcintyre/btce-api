import sys
import time

import wx
import matplotlib
matplotlib.use("WXAgg")
matplotlib.rcParams['toolbar'] = 'None'

import matplotlib.pyplot as plt
import pylab

import btceapi


class Chart(object):
    def __init__(self, symbol):
        self.symbol = symbol
        self.base = symbol.split("_")[0].upper()
        self.alt = symbol.split("_")[1].upper()

        self.ticks = btceapi.getTradeHistory(self.symbol)
        self.last_tid = max([t.tid for t in self.ticks])

        self.fig = plt.figure()
        self.axes = self.fig.add_subplot(111)
        self.bid_line, = self.axes.plot(*zip(*self.bid), \
                linestyle='None', marker='o', color='red')
        self.ask_line, = self.axes.plot(*zip(*self.ask), \
                linestyle='None', marker='o', color='green')
        
        self.fig.canvas.draw()

        self.timer_id = wx.NewId()
        self.actor = self.fig.canvas.manager.frame
        self.timer = wx.Timer(self.actor, id=self.timer_id)
        self.timer.Start(10000) # update every 10 seconds
        wx.EVT_TIMER(self.actor, self.timer_id, self.update)

        pylab.show()

    @property
    def bid(self):
        return [(t.date, t.price) for t in self.ticks if t.trade_type == u'bid']

    @property
    def ask(self):
        return [(t.date, t.price) for t in self.ticks if t.trade_type == u'ask']

    def update(self, event):
        ticks = btceapi.getTradeHistory(self.symbol)
        self.ticks += [t for t in ticks if t.tid > self.last_tid]

        for t in ticks:
            if t.tid > self.last_tid:
                print "%s: %s %f at %s %f" % \
                        (t.trade_type, self.base, t.amount, self.alt, t.price)

        self.last_tid = max([t.tid for t in ticks])

        x, y = zip(*self.bid)
        self.bid_line.set_xdata(x)
        self.bid_line.set_ydata(y)

        x, y = zip(*self.ask)
        self.ask_line.set_xdata(x)
        self.ask_line.set_ydata(y)

        pylab.gca().relim()
        pylab.gca().autoscale_view()

        self.fig.canvas.draw()


if __name__ == "__main__":
    symbol = "btc_usd"
    try:
        symbol = sys.argv[1]
    except IndexError:
        pass

    chart = Chart(symbol)

