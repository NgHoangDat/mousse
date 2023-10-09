import operator

from ..functional import compose, peek_nth, sort

fifo = compose(peek_nth(0), sort(key=operator.attrgetter("earliest")))
lifo = compose(peek_nth(0), reversed, sort(key=operator.attrgetter("earliest")))
lru = compose(peek_nth(0), sort(key=operator.attrgetter("latest")))
mru = compose(peek_nth(0), reversed, sort(key=operator.attrgetter("latest")))
lfu = compose(peek_nth(0), sort(key=operator.attrgetter("count")))
