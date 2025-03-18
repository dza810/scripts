




class Route:
    def __init__(self, nex, dist):
        assert dist >= 0
        self.nex = nex
        self.dist = dist

    def update(self, n, d):
        assert d >= 0
        if d < self.dist:
            self.nex = n
            self.dist = d

    def __str__(self):
        return f"{self.dist} via {self.nex.name}"


class Node:
    def __init__(self, name):
        self.name = name
        self.min_dist = { self.name: Route(self, 0) }
        self.connected = set()

    def connect(self, node):
        self.connected.add(node)

    def update_recv(self, node, dist):
        self.min_dist[node.name] = Route(node, 1)
        for n, nd in dist.items():
            if n in self.min_dist:
                self.min_dist[n].update(node, nd.dist + 1)
            else:
                self.min_dist[n] = Route(node, nd.dist + 1)

    def update_send(self):
        for con in self.connected:
            con.update_recv(self, self.min_dist)

def connect(x, y):
    x.connect(y)
    y.connect(x)

a = Node("A")
b = Node("B")
c = Node("C")
d = Node("D")
e = Node("E")

nodes = [a,b,c,d, e]

connect(a, b)
connect(b, c)
connect(c, d)
connect(c, e)

for i in range(3):
    for n in nodes:
        n.update_send()

for n in nodes:
    print(f"** {n.name}")
    for nn, nnd in n.min_dist.items():
        print(f"  {n.name} <-> {nn}: {nnd}")
    print()



