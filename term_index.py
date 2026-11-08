"""Exact multi-term matching for already identified redaction values."""

from collections import deque


class TermIndex:
    def __init__(self, terms: list[str]) -> None:
        self.nodes: list[dict[str, int]] = [{}]
        self.fail = [0]
        self.outputs: list[list[str]] = [[]]
        for term in dict.fromkeys(terms):
            if not term:
                continue
            state = 0
            for char in term:
                if char not in self.nodes[state]:
                    self.nodes[state][char] = len(self.nodes)
                    self.nodes.append({})
                    self.fail.append(0)
                    self.outputs.append([])
                state = self.nodes[state][char]
            self.outputs[state].append(term)
        queue = deque(self.nodes[0].values())
        while queue:
            state = queue.popleft()
            for char, child in self.nodes[state].items():
                queue.append(child)
                fallback = self.fail[state]
                while fallback and char not in self.nodes[fallback]:
                    fallback = self.fail[fallback]
                self.fail[child] = self.nodes[fallback].get(char, 0)
                self.outputs[child].extend(self.outputs[self.fail[child]])

    def find(self, text: str):
        state = 0
        last_end: dict[str, int] = {}
        for index, char in enumerate(text):
            while state and char not in self.nodes[state]:
                state = self.fail[state]
            state = self.nodes[state].get(char, 0)
            for term in self.outputs[state]:
                start, end = index + 1 - len(term), index + 1
                if start >= last_end.get(term, 0):
                    last_end[term] = end
                    yield term, start, end
