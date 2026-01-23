import heapq
from dataclasses import dataclass, field

from request.AbstractData.AbstractMulticastData import AbstractMulticastData


@dataclass(order=True)
class PrioritizedItem:
    priority: int
    item: AbstractMulticastData = field(compare=False)


@dataclass
class UniquePriorityQueue:
    """Priority queue with unique priorities."""
    _heap: list[int] = field(default_factory=list)
    _entries: dict[int, AbstractMulticastData] = field(default_factory=dict)

    def put(self, priority: int, item: AbstractMulticastData) -> bool:
        """Add item. Returns False if priority already exists."""
        if priority in self._entries:
            return False
        self._entries[priority] = item
        heapq.heappush(self._heap, priority)
        return True

    def get(self) -> PrioritizedItem | None:
        """Remove and return lowest priority item."""
        while self._heap:
            priority = heapq.heappop(self._heap)
            if priority in self._entries:
                return PrioritizedItem(priority, self._entries.pop(priority))
        return None

    def peek(self) -> PrioritizedItem | None:
        """Return lowest priority item without removing."""
        while self._heap:
            priority = self._heap[0]
            if priority in self._entries:
                return PrioritizedItem(priority, self._entries[priority])
            heapq.heappop(self._heap)  # Clean up stale entry
        return None

    def empty(self) -> bool:
        return len(self._entries) == 0

    def __contains__(self, priority: int) -> bool:
        return priority in self._entries
