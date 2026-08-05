#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20241219

'''
Optimized Path Search for Power Tree (BFS for Shortest Path)
1. Supports multiple VRMs (startNodes) and Sinks (endNodes).
2. Uses BFS to ensure shortest path is found first.
3. Filters:
   - Exclude Capacitors (unless explicitly in includeComps).
   - Exclude components with PinCount > maxPinCount UNLESS they are PTH (R, L, FB) OR in includeComps.
   - Exclude nets matching excludedNets patterns.
   - Stop when Sink is reached (Shortest path retained).
   - FORCE INCLUDE components in includeComps.
4. Optimization:
   - Once a specific Sink (Component:Net) is found, ignore subsequent attempts to reach it.
   - Outputs the actual max search depth reached.
'''

import re
from collections import deque
from ..common.common import log, regAnyMatch
from ..common.complexDict import ComplexDict
from ..primitive.pin import Pin

class Node(ComplexDict):
    '''
    Composed of pins objects
    node Type: VRM, Sink, Mid, Start, End
    '''
    def __init__(self, node):
        if isinstance(node, Node):
            super(self.__class__, self).__init__()
            self.update(node)
            return
        
        if isinstance(node, (list, tuple)):
            component, net = node
        else:
            log.exception("node must be Node, list, or tuple")
            return

        super(self.__class__, self).__init__()
        
        self.updates({
            "Component": component,
            "Net": net,
            "Type": "Mid",  # Start, Mid, End
            "Previous": [],
            "Next": []
        })
        
        self.update("self", self)
        
        maps = {"name": {
            "Key": "self",
            "Get": lambda s: "%s:%s" % (s.Component, s.Net)
        }}
        self.setMaps(maps)

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.Component == other.Component and self.Net == other.Net

    def __hash__(self):
        return hash((self.Component, self.Net))


class Path(object):
    '''
    Optimized Path finder supporting multiple starts and ends using BFS.
    '''
    
    def __init__(self, startNodes=None, endNodes=None, includeComps=None, excludedNets=None, layout=None):
        self._startNodes = []
        self._endNodes = []
        
        # Default excluded nets
        self.excludedNets = excludedNets if excludedNets else [".*GND.*"]
        
        # Additional components to force include
        self.includeComps = includeComps if includeComps else []

        # Pass-Through-Hole components pattern (Resistor, Inductor, Ferrite Bead)
        self.PTH_PATTERNS = ["R.*", "L.*", "FB.*"]
        
        self.maxPinCount = 4
        self._maxSearchDepthLimit = 10  # Limit to prevent infinite loops
        self._actualMaxDepth = 0         # Track actual depth reached
        
        self.layout = layout
        self.nodes = []  # All unique nodes found in the path tree
        self._visited = set()  # Track visited (Component, Net) to avoid cycles
        self._foundSinks = set() # Track names of sinks already found
        
        # Initialize nodes if provided
        if startNodes:
            self.startNodes = startNodes
        if endNodes:
            self.endNodes = endNodes

    @property
    def startNodes(self):
        return self._startNodes

    @startNodes.setter
    def startNodes(self, nodes):
        self._startNodes = []
        for node in nodes:
            n = Node(node)
            n.Type = "Start"
            self._startNodes.append(n)
            
    @property
    def endNodes(self):
        return self._endNodes

    @endNodes.setter
    def endNodes(self, nodes):
        self._endNodes = []
        seen = set()
        for node in nodes:
            n = Node(node)
            # Avoid duplicate end nodes
            if n.name not in seen:
                n.Type = "End"
                self._endNodes.append(n)
                seen.add(n.name)

    @property
    def nets(self):
        return list(set([n.Net for n in self.nodes]))
    
    @property
    def comps(self):
        return list(set([n.Component for n in self.nodes]))
    
    def insertNode(self, node, parent=None):
        """
        Adds node to the global list and links it to the parent.
        Returns the node instance stored in self.nodes (either new or existing).
        """
        # Check if node already exists in our global collection by name
        existing_node = None
        for n in self.nodes:
            if n.name == node.name:
                existing_node = n
                break
        
        if existing_node:
            # Link parent to existing node if not already linked
            if parent and existing_node not in parent.Next:
                parent.Next.append(existing_node)
                if parent not in existing_node.Previous:
                    existing_node.Previous.append(parent)
            return existing_node
        else:
            self.nodes.append(node)
            if parent:
                parent.Next.append(node)
                node.Previous.append(parent)
            return node

    def search(self):
        if not self._startNodes:
            log.info("StartNodes must be set before search path.")
            return None
        if not self._endNodes:
            log.info("EndNodes must be set before search path.")
            return None
        
        log.info("Starting BFS path search from %d sources to %d sinks." % (len(self._startNodes), len(self._endNodes)))
        
        # Reset state
        self.nodes = []
        self._visited = set()
        self._foundSinks = set()
        self._actualMaxDepth = 0
        
        # Create a map of end nodes for quick lookup: Key: Component, Value: List of Nodes
        self._endNodeMap = {}
        for en in self._endNodes:
            if en.Component not in self._endNodeMap:
                self._endNodeMap[en.Component] = []
            self._endNodeMap[en.Component].append(en)

        # Initialize Queue for BFS: (Node, Depth)
        queue = deque()
        
        for startNode in self._startNodes:
            insertedStart = self.insertNode(startNode)
            self._visited.add((startNode.Component, startNode.Net))
            queue.append((insertedStart, 0))
            
        # Perform BFS
        while queue:
            currentNode, depth = queue.popleft()
            
            # Update actual max depth
            if depth > self._actualMaxDepth:
                self._actualMaxDepth = depth
                
            # Check depth limit
            if depth >= self._maxSearchDepthLimit:
                continue
            
            self._bfs_step(currentNode, depth, queue)

        self.removeInvalidNodes()
        log.info("Search complete. Found %d nodes. Max Depth Reached: %d/%d" % (len(self.nodes), self._actualMaxDepth,self._maxSearchDepthLimit))

    def _bfs_step(self, currentNode, depth, queue):
        """
        Process one step of BFS: find neighbors and add to queue.
        """
        net = currentNode.Net
        startComp = currentNode.Component
        
        # Get all pins on this net
        if net not in self.layout.Nets:
            return
            
        pins = self.layout.Nets[net].Objects.Pins
        if not pins:
            return

        # Get unique components connected to this net, excluding the current component
        comps = set()
        for p in pins:
            try:
                pinObj = Pin(p, self.layout)
                compName = pinObj.CompName
                if compName and compName != startComp:
                    comps.add(compName)
            except:
                continue

        for comp in comps:
            # 1. Check if this component is a Sink (End Node)
            isSink = False
            if comp in self._endNodeMap:
                for endNodeCandidate in self._endNodeMap[comp]:
                    if endNodeCandidate.Net == net:
                        sinkName = endNodeCandidate.name
                        
                        # If this sink was already found, skip
                        if sinkName in self._foundSinks:
                            continue
                        
                        # Found a new sink (Shortest path guaranteed by BFS)
                        endNode = Node([comp, net])
                        endNode.Type = "End"
                        self.insertNode(endNode, currentNode)
                        
                        # Mark as found
                        self._foundSinks.add(sinkName)
                        isSink = True
                        # Do not traverse further from a Sink, so we don't add to queue
                        break 
            
            if isSink:
                continue

            # 2. Filter Components for Traversal
            
            # Get component properties
            compObj = self.layout.Components.get(comp)
            if not compObj:
                continue
                
            partType = compObj.PartType
            pinCount = compObj.PinCount
            
            # Check if component is forced included
            isForcedInclude = comp in self.includeComps
            
            # Check if it's a PTH component (Resistor, Inductor, FB)
            isPth = regAnyMatch(self.PTH_PATTERNS, comp)
            
            # Filtering Logic:
            if not isForcedInclude:
                # Exclude Capacitors
                if partType == "Capacitor":
                    continue
                
                # Exclude high pin count components unless they are PTH
                if not isPth and pinCount > self.maxPinCount:
                    continue

            # 3. Traverse Nets of this Component
            for newNet in compObj.NetNames:
                if newNet == net:
                    continue
                
                # Exclude specific nets (e.g., GND)
                if regAnyMatch(self.excludedNets, newNet):
                    continue
                
                # Check Cycle/Visited
                nodeKey = (comp, newNet)
                # print(nodeKey)
                if nodeKey in self._visited:
                    continue
                
                # Mark as visited
                self._visited.add(nodeKey)
                
                # Create new Node
                newNode = Node([comp, newNet])
                insertedNode = self.insertNode(newNode, currentNode)
                
                # Add to queue for next level processing
                queue.append((insertedNode, depth + 1))

    def removeInvalidNodes(self):
        """
        Remove nodes that are not connected to either Start or End properly 
        (i.e., dead ends that are not Sinks).
        """
        changed = True
        while changed:
            changed = False
            nodesToRemove = []
            for node in self.nodes:
                if node.Type in ["Start", "End"]:
                    continue
                
                if not node.Next and not node.Previous:
                    nodesToRemove.append(node)
                    changed = True
                elif not node.Next and node.Type != "End":
                    # Dead end that isn't a sink
                    nodesToRemove.append(node)
                    changed = True
                    
            for node in nodesToRemove:
                self.removeNode(node)

    def removeNode(self, node):
        if node in self.nodes:
            self.nodes.remove(node)
        
        # Clean up links
        for prevNode in node.Previous:
            if node in prevNode.Next:
                prevNode.Next.remove(node)
        
        for nextNode in node.Next:
            if node in nextNode.Previous:
                nextNode.Previous.remove(node)
                
        node.Previous.clear()
        node.Next.clear()

    def printTree(self, startNode=None, prefix='    '):
        if not startNode:
            if not self._startNodes:
                return
            log.info("Power Tree:")
            for sn in self._startNodes:
                log.info(sn.name)
                self.printTree(sn, prefix)
            return

        if not startNode.Next:
            return

        for item in startNode.Next:
            log.info("%s|__ %s (%s)" % (prefix, item.name, item.Type))
            self.printTree(item, prefix + '    ')