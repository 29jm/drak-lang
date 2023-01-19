from typing import Dict, Set, TypeVar

T = TypeVar("T")
C = TypeVar("C")
def color(graph: Dict[T, Set[T]], colors: Set[C]) -> Dict[T, C]|None:
    # No graph, no coloring needed
    if not graph:
        return {}

    # Pick a potentially colorable node, or fail entirely
    picked = next((n for n in graph if len(graph[n]) < len(colors)), None)
    if not picked:
        print("not colorable!")
        return

    # We have at least one low degree node, remove it and color the rest
    graphbis = { node: { edge for edge in graph[node] if edge != picked }
                    for node in graph.keys() if node != picked }
    coloring = color(graphbis, colors)

    # If the reduced graph was colorable, paint in the node we excluded
    if coloring != None:
        taken = set(coloring[adjacent] for adjacent in graph[picked])
        coloring[picked] = (colors - taken).pop()

    return coloring