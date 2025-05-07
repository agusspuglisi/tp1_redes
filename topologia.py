from typing import Any, cast
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.topo import Topo


class Topo(Topo):
    def build(self, **_opts):
        s1 = self.addSwitch("s1")
        h1 = self.addHost("h1", ip="10.0.0.2/30", defaultRoute="via 10.0.0.1")
        h2 = self.addHost("h2", ip="10.0.0.6/30", defaultRoute="via 10.0.0.5")

        self.addLink(h2, s1, loss = 10) 
        self.addLink(h1, s1, loss = 10) 
        


def run():
    topo = Topo()
    net = Mininet(topo=topo)
    net.start()

    CLI(net)
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run()