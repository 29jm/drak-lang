from typing import Dict, Set, List, TypeVar
from drak.compiler.ir_utils import Instr, vars_written_by, vars_read_by, is_fixed_alloc_variable
from drak.compiler.liveness import global_igraph, rename

T = TypeVar("T")
C = TypeVar("C")
def color(graph: Dict[T, Set[T]], colors: Set[C], fixed_colors: Dict[T, C]) -> Dict[T, C]|None:
    # No graph, no coloring needed
    if not graph:
        return fixed_colors

    # Pick a potentially colorable node, or fail entirely
    picked = next((n for n in graph if len(graph[n]) < len(colors)), None)
    if not picked:
        print("not colorable!")
        return

    # We have at least one low degree node, remove it and color the rest
    graphbis = { node: { edge for edge in graph[node] if edge != picked }
                    for node in graph.keys() if node != picked }
    coloring = color(graphbis, colors, fixed_colors)

    # If the reduced graph was colorable, paint in the node we excluded, if needed
    if coloring != None and picked not in coloring:
        taken = set(coloring[adjacent] for adjacent in graph[picked])
        coloring[picked] = (colors - taken).pop()

    return coloring

def spillvars(bblocks: List[List[Instr]], spills: Dict[str, str]):
    """Spills @spills.keys() (e.g. REG13.1) into @spills.values() (e.g. REGSPILL.4)."""
    n, i = 0, 0
    stackspace = 4 * len(spills) + 4
    stackrefs = {var: -(4+4*n) for (n, var) in enumerate(spills.keys())}

    print(f'Spilling {spills.keys()}')
    bblocks[0].insert(2, ['sub', 'sp', 'sp', f'#{stackspace}'])

    while n < len(bblocks):
        i = 0
        while i < len(bblocks[n]):
            instr = bblocks[n][i]
            added_instrs = 0
            read = set(spills.keys()) & set(vars_read_by(instr))
            writ = set(spills.keys()) & set(vars_written_by(instr))

            for var in writ:
                bblocks[n].insert(i+1, ['str', var, ['sp', f'#{stackrefs[var]}']])
                added_instrs += 1
            for var in read:
                bblocks[n].insert(i, ['ldr', var, ['sp', f'#{stackrefs[var]}']])
                added_instrs += 1

            i += 1 + added_instrs
        n += 1
    return bblocks

def spillcosts(bblocks: List[List[Instr]], vars: set) -> Dict[str, int]:
    costs: Dict[str, int] = {}
    for block in bblocks:
        for instr in block:
            for var in vars & (set(vars_read_by(instr)) | set(vars_written_by(instr))):
                if not var in costs:
                    costs[var] = 1
                else:
                    costs[var] += 1
    return costs

def regalloc(bblocks: List[List[Instr]], regs: Set[str]) -> List[List[Instr]]:
    """"Allocates registers in @regs to variables in @bblocks, given the interference
    graph in @graph.
    """
    done: bool = False
    spills = []
    graph = global_igraph(bblocks)
    fixed_colors: Dict[str, str] = {}

    for node, deps in graph.items():
        for n in deps | set([node]):
            if not is_fixed_alloc_variable(n):
                continue
            fixed_colors[n] = f'r{n.removeprefix("REGF")}'

    while not done:
        coloring = color(graph, regs, fixed_colors)

        if coloring != None:
            break

        # Compute spill costs per variable
        costs = spillcosts(bblocks, set(graph.keys()))

        # Spill the least costly variable that's still reasonably connected
        spilled = min(costs, key=lambda n: costs[n]/(len(graph[n])+0.5))
        spills.append(spilled)

        # Update the graph
        graph = { node: { edge for edge in graph[node] if edge != spilled }
                        for node in graph.keys() if node != spilled }

    if spills:
        spilldict = {var: f'REGSPILL{i}' for i, var in enumerate(spills)}
        bblocks = spillvars(bblocks, spilldict)

    # Recompute and recolor the graph
    graph = global_igraph(bblocks)
    coloring = color(graph, regs, fixed_colors)
    if coloring == None:
        return regalloc(bblocks, regs)

    # Apply the colors
    for var, reg in coloring.items():
        bblocks = rename(bblocks, var, reg)

    return bblocks